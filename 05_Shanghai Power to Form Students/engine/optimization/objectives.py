from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import geopandas as gpd
from shapely.ops import unary_union


FLOOR_HEIGHT_M = 3.5


@dataclass(frozen=True)
class ObjectiveContext:
    site_area: float
    baseline_gfa: float
    residential_gfa: float
    baseline_union: object
    street_access: object
    street_access_buffer_m: float


def _gfa(frame: gpd.GeoDataFrame) -> float:
    return float((frame.geometry.area * frame["height_m"] / FLOOR_HEIGHT_M).sum())


def build_objective_context(
    baseline: gpd.GeoDataFrame,
    boundary: gpd.GeoDataFrame,
    streets: gpd.GeoDataFrame,
    scenario: dict,
    objective_config: dict | None = None,
) -> ObjectiveContext:
    base_res = baseline[baseline["residential_proxy"].fillna(False)]
    measurement = (objective_config or {}).get("measurement", {})
    street_buffer_m = float(measurement.get("street_access_buffer_m", 5.0))
    return ObjectiveContext(
        site_area=float(boundary.geometry.union_all().area),
        baseline_gfa=_gfa(baseline),
        residential_gfa=_gfa(base_res),
        baseline_union=unary_union(list(baseline.geometry)),
        street_access=unary_union(list(streets.geometry)).buffer(street_buffer_m),
        street_access_buffer_m=street_buffer_m,
    )


def evaluate_objectives(
    baseline: gpd.GeoDataFrame,
    candidate: gpd.GeoDataFrame,
    changes: list[dict],
    boundary: gpd.GeoDataFrame,
    streets: gpd.GeoDataFrame,
    scenario: dict,
    context: ObjectiveContext | None = None,
    objective_config: dict | None = None,
) -> tuple[dict[str, float], dict[str, float]]:
    context = context or build_objective_context(
        baseline, boundary, streets, scenario, objective_config
    )
    site_area = context.site_area
    changed_ids = {item["bid"] for item in changes}
    base_res = baseline[baseline["residential_proxy"].fillna(False)]
    changed_res = base_res[base_res["bid"].astype(str).isin(changed_ids)]
    residential_total = context.residential_gfa
    residential_disruption = _gfa(changed_res) / residential_total if residential_total > 0 else 0.0

    base_gfa = context.baseline_gfa
    candidate_gfa = _gfa(candidate)
    base_by_id = baseline.set_index(baseline["bid"].astype(str))
    candidate_by_id = candidate.set_index(candidate["bid"].astype(str))
    positive_gfa_increment_m2 = 0.0
    minimum_gfa_change_m2 = float(
        (objective_config or {}).get("numerical_resolution", {}).get(
            "minimum_building_gfa_change_m2", 1.0
        )
    )
    for bid in candidate_by_id.index:
        candidate_row = candidate_by_id.loc[bid]
        candidate_building_gfa = (
            float(candidate_row.geometry.area) * float(candidate_row["height_m"]) / FLOOR_HEIGHT_M
        )
        baseline_building_gfa = 0.0
        if bid in base_by_id.index:
            baseline_row = base_by_id.loc[bid]
            baseline_building_gfa = (
                float(baseline_row.geometry.area) * float(baseline_row["height_m"]) / FLOOR_HEIGHT_M
            )
        increment = candidate_building_gfa - baseline_building_gfa
        if increment >= minimum_gfa_change_m2:
            positive_gfa_increment_m2 += increment
    development_capacity = (
        positive_gfa_increment_m2 / site_area if site_area > 0 else 0.0
    )

    # Current morphology operators only preserve or shrink footprints. Computing
    # the union of all 1,370 buildings for every candidate is unnecessary: start
    # with the released pieces of changed buildings, then remove any area still
    # covered by nearby candidate buildings (including legacy overlaps).
    released_parts = []
    for bid in changed_ids:
        if bid not in base_by_id.index or bid not in candidate_by_id.index:
            continue
        released_part = base_by_id.loc[bid].geometry.difference(
            candidate_by_id.loc[bid].geometry
        )
        if not released_part.is_empty and released_part.area > 1e-9:
            released_parts.append(released_part)
    if released_parts:
        potential_release = unary_union(released_parts)
        nearby_indices = candidate.sindex.query(potential_release, predicate="intersects")
        nearby_cover = unary_union(list(candidate.iloc[nearby_indices].geometry))
        released = potential_release.difference(nearby_cover)
    else:
        released = context.baseline_union.difference(context.baseline_union)
    connected_released = released.intersection(context.street_access)
    released_ratio = float(connected_released.area / site_area) if site_area > 0 else 0.0

    op_counts = Counter(item["operator"] for item in changes)
    changed_stakeholders = Counter(
        baseline.loc[baseline["bid"].astype(str).isin(changed_ids), "stakeholder_proxy"]
        .fillna("unknown")
        .astype(str)
    )
    objectives = {
        "residential_disruption": float(residential_disruption),
        "development_capacity": float(development_capacity),
        "street_connected_released_ground": float(released_ratio),
    }
    heights = candidate["height_m"].astype(float)
    descriptors = {
        "far": candidate_gfa / site_area if site_area > 0 else 0.0,
        "coverage": float(candidate.geometry.area.sum() / site_area) if site_area > 0 else 0.0,
        "height_mean_m": float(heights.mean()),
        "height_max_m": float(heights.max()),
        "changed_buildings": float(len(changed_ids)),
        "positive_gfa_increment_m2": float(positive_gfa_increment_m2),
        "net_gfa_change_m2": float(candidate_gfa - base_gfa),
        "net_gfa_change_far": float((candidate_gfa - base_gfa) / site_area)
        if site_area > 0 else 0.0,
        "street_access_buffer_m": context.street_access_buffer_m,
        "densify_count": float(op_counts.get("densify", 0)),
        "open_ground_count": float(op_counts.get("open_ground", 0)),
        "parameter_count": float(op_counts.get("parameter_height_footprint", 0)),
        "changed_resident_buildings": float(changed_stakeholders.get("resident", 0)),
        "changed_developer_buildings": float(changed_stakeholders.get("developer", 0)),
        "changed_state_buildings": float(changed_stakeholders.get("state", 0)),
        "changed_unknown_buildings": float(changed_stakeholders.get("unknown", 0)),
    }
    return objectives, descriptors

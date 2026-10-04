from __future__ import annotations

import math
from typing import Any

import geopandas as gpd
import pandas as pd
from shapely import affinity
from shapely.geometry import LineString, MultiPolygon, Polygon, box
from shapely.ops import nearest_points, unary_union

from .models import ZoneDecision


FLOOR_HEIGHT_M = 3.5


def operator_policy(scenario: dict[str, Any] | None) -> tuple[set[str], dict[str, set[str]], dict[str, float]]:
    policy = (scenario or {}).get("operator_policy", {})
    allowed = set(policy.get("allowed_operators", ("densify", "open_ground")))
    targets = {
        name: set(values)
        for name, values in policy.get("stakeholder_targets", {}).items()
    }
    limits = {name: float(value) for name, value in policy.get("maximum_intensity", {}).items()}
    return allowed, targets, limits


def _eligible_for_operator(rows: gpd.GeoDataFrame, operator: str, scenario: dict[str, Any] | None):
    allowed, targets, _ = operator_policy(scenario)
    if operator == "public_space_reconfiguration":
        mask = ~rows["heritage"].fillna(False)
    else:
        mask = rows["editable"].fillna(False) & ~rows["heritage"].fillna(False)
    if operator not in allowed:
        return mask & False
    stakeholder_targets = targets.get(operator)
    if stakeholder_targets:
        mask &= rows["stakeholder_proxy"].astype(str).isin(stakeholder_targets)
    return mask


def _control_map(controls: pd.DataFrame | None) -> dict[str, dict[str, Any]]:
    if controls is None:
        return {}
    return {str(row["zone_id"]): row.to_dict() for _, row in controls.iterrows()}


def _zone_area_map(zones: gpd.GeoDataFrame | None) -> dict[str, float]:
    if zones is None or zones.empty:
        return {}
    return {
        str(row["zone_id"]): float(row.geometry.area)
        for _, row in zones.iterrows()
    }


def build_operator_availability(
    baseline: gpd.GeoDataFrame,
    zones: gpd.GeoDataFrame,
    controls: pd.DataFrame | None,
    scenario: dict[str, Any] | None = None,
    operator_specs: dict[str, Any] | None = None,
) -> dict[str, tuple[str, ...]]:
    """Return operators that can produce a non-zero change in each zone."""
    control_by_zone = _control_map(controls)
    area_by_zone = _zone_area_map(zones)
    operator_specs = operator_specs or {}
    split_minimum_area = float(
        operator_specs.get("split_to_towers", {}).get("parameters", {}).get(
            "minimum_building_area_m2", 300.0
        )
    )
    step_distance = float(
        operator_specs.get("heritage_step_down", {}).get("parameters", {}).get(
            "influence_distance_m", 80.0
        )
    )
    sensitive = baseline[
        baseline["heritage"].fillna(False) | baseline["residential_proxy"].fillna(False)
    ]
    sensitive_union = unary_union(list(sensitive.geometry)) if not sensitive.empty else None
    availability: dict[str, tuple[str, ...]] = {}
    for zone_id in zones["zone_id"].astype(str):
        zone_rows = baseline[baseline["zone_id"].astype(str).eq(zone_id)]
        allowed = ["noop"]
        for footprint_operator in (
            "open_ground",
            "public_space_reconfiguration",
            "courtyard_access_improvement",
        ):
            eligible_rows = zone_rows[
                _eligible_for_operator(zone_rows, footprint_operator, scenario)
            ]
            if not eligible_rows.empty:
                allowed.append(footprint_operator)
        densify_eligible = zone_rows[_eligible_for_operator(zone_rows, "densify", scenario)]
        if not densify_eligible.empty:
            control = control_by_zone.get(zone_id, {})
            height_limit = float(control.get("height_limit_m", math.inf))
            has_height_headroom = any(
                float(row["height_m"]) < max(float(row["height_m"]), height_limit) - 1e-7
                for _, row in densify_eligible.iterrows()
            )
            zone_area = area_by_zone.get(zone_id)
            max_far = pd.to_numeric(control.get("max_far"), errors="coerce")
            has_far_headroom = True
            if zone_area is not None and zone_area > 0 and pd.notna(max_far):
                current_gfa = float(
                    (zone_rows.geometry.area * zone_rows["height_m"] / FLOOR_HEIGHT_M).sum()
                )
                current_far = current_gfa / zone_area
                has_far_headroom = float(max_far) > current_far + 1e-9
            if has_height_headroom and has_far_headroom:
                allowed.append("densify")
        split_eligible = zone_rows[_eligible_for_operator(zone_rows, "split_to_towers", scenario)]
        if (
            not split_eligible.empty
            and split_eligible.geometry.area.ge(split_minimum_area).any()
        ):
            allowed.append("split_to_towers")
        step_eligible = zone_rows[_eligible_for_operator(zone_rows, "heritage_step_down", scenario)]
        if len(step_eligible) >= 2 and sensitive_union is not None:
            distances = [
                min(float(geom.centroid.distance(sensitive_union)), step_distance)
                for geom in step_eligible.geometry
            ]
            if max(distances) - min(distances) > 1e-6:
                allowed.append("heritage_step_down")
        availability[zone_id] = tuple(allowed)
    return availability


def build_operator_impact_counts(
    baseline: gpd.GeoDataFrame,
    zones: gpd.GeoDataFrame,
    controls: pd.DataFrame | None,
    scenario: dict[str, Any] | None = None,
    operator_specs: dict[str, Any] | None = None,
) -> dict[tuple[str, str], int]:
    """Conservative count of buildings an active operator can modify."""
    availability = build_operator_availability(
        baseline, zones, controls, scenario, operator_specs
    )
    control_by_zone = _control_map(controls)
    impacts: dict[tuple[str, str], int] = {}
    for zone_id in zones["zone_id"].astype(str):
        zone_rows = baseline[baseline["zone_id"].astype(str).eq(zone_id)]
        densify_eligible = zone_rows[_eligible_for_operator(zone_rows, "densify", scenario)]
        impacts[(zone_id, "noop")] = 0
        for operator in (
            "open_ground",
            "split_to_towers",
            "heritage_step_down",
            "public_space_reconfiguration",
            "courtyard_access_improvement",
        ):
            eligible = zone_rows[_eligible_for_operator(zone_rows, operator, scenario)]
            impacts[(zone_id, operator)] = (
                int(len(eligible)) if operator in availability[zone_id] else 0
            )
        if "densify" not in availability[zone_id]:
            impacts[(zone_id, "densify")] = 0
            continue
        height_limit = float(control_by_zone.get(zone_id, {}).get("height_limit_m", math.inf))
        impacts[(zone_id, "densify")] = int(sum(
            float(row["height_m"]) < max(float(row["height_m"]), height_limit) - 1e-7
            for _, row in densify_eligible.iterrows()
        ))
    return impacts


def _split_with_central_gap(geometry, gap_ratio: float):
    """Cut a narrow cross-axis gap while keeping the parts in one building record."""
    hull = geometry.convex_hull
    points = list(hull.exterior.coords)
    edges = [
        (points[index + 1][0] - points[index][0],
         points[index + 1][1] - points[index][1])
        for index in range(len(points) - 1)
    ]
    long_edge = max(edges, key=lambda edge: math.hypot(*edge))
    angle = math.degrees(math.atan2(long_edge[1], long_edge[0]))
    center = geometry.centroid.coords[0]
    aligned = affinity.rotate(geometry, -angle, origin=center)
    minx, miny, maxx, maxy = aligned.bounds
    gap = max((maxx - minx) * gap_ratio, 0.5)
    cutter = box((minx + maxx - gap) / 2, miny - 1, (minx + maxx + gap) / 2, maxy + 1)
    cut = aligned.difference(cutter)
    polygons = [part for part in getattr(cut, "geoms", [cut]) if part.geom_type == "Polygon" and part.area > 1]
    if len(polygons) < 2:
        return geometry
    return affinity.rotate(MultiPolygon(polygons), angle, origin=center)


def _limited_cut(geometry, cutter_for_scale, minimum_ratio: float):
    """Apply the strongest cut that retains the configured footprint ratio."""
    minimum_area = geometry.area * minimum_ratio
    best = geometry
    low, high = 0.0, 1.0
    for _ in range(7):
        scale = (low + high) / 2
        candidate = geometry.difference(cutter_for_scale(scale))
        if not candidate.is_empty and candidate.area >= minimum_area:
            best = candidate
            low = scale
        else:
            high = scale
    return best


def _street_facing_setback_cutter(geometry, street_union, depth: float):
    """Return a shallow rectangular cut oriented from the nearest street inward."""
    road_point, _ = nearest_points(street_union, geometry.centroid)
    _, entry = nearest_points(road_point, geometry)
    cx, cy = geometry.centroid.coords[0]
    ex, ey = entry.coords[0]
    dx, dy = cx - ex, cy - ey
    length = math.hypot(dx, dy)
    if length <= 1e-9:
        return entry.buffer(0)
    ux, uy = dx / length, dy / length
    tx, ty = -uy, ux
    span = math.hypot(
        geometry.bounds[2] - geometry.bounds[0],
        geometry.bounds[3] - geometry.bounds[1],
    )
    outside_x, outside_y = ex - ux * 0.25, ey - uy * 0.25
    return Polygon([
        (outside_x - tx * span, outside_y - ty * span),
        (outside_x + tx * span, outside_y + ty * span),
        (ex + ux * depth + tx * span, ey + uy * depth + ty * span),
        (ex + ux * depth - tx * span, ey + uy * depth - ty * span),
    ])


def apply_decisions(
    baseline: gpd.GeoDataFrame,
    decisions: list[ZoneDecision],
    controls: pd.DataFrame | None,
    operator_specs: dict[str, Any],
    zones: gpd.GeoDataFrame | None = None,
    scenario: dict[str, Any] | None = None,
    minimum_change: dict[str, float] | None = None,
    streets: gpd.GeoDataFrame | None = None,
) -> tuple[gpd.GeoDataFrame, list[dict[str, Any]]]:
    """Apply explicit zone decisions and return a fresh state plus a per-building log."""
    result = baseline.copy(deep=True)
    result["applied_operator"] = "noop"
    result["operator_intensity"] = 0.0
    changes: list[dict[str, Any]] = []
    control_by_zone = _control_map(controls)
    area_by_zone = _zone_area_map(zones)
    minimum_change = minimum_change or {}
    minimum_gfa_change = float(
        minimum_change.get("minimum_building_gfa_change_m2", 1.0)
    )
    minimum_footprint_change = float(
        minimum_change.get("minimum_building_footprint_change_m2", 1.0)
    )
    minimum_height_change = float(
        minimum_change.get("minimum_building_height_change_m", 0.1)
    )
    street_union = (
        unary_union(list(streets.geometry))
        if streets is not None and not streets.empty
        else None
    )

    for decision in decisions:
        if decision.operator == "noop":
            continue
        if decision.operator not in operator_specs:
            raise KeyError(f"未登记算子：{decision.operator}")
        if not 0.0 <= decision.intensity <= 1.0:
            raise ValueError(f"算子强度必须在 0–1：{decision}")
        allowed, _, intensity_limits = operator_policy(scenario)
        if decision.operator not in allowed:
            continue
        intensity = min(float(decision.intensity), intensity_limits.get(decision.operator, 1.0))
        zone_mask = result["zone_id"].astype(str).eq(str(decision.zone_id))
        eligible = zone_mask & _eligible_for_operator(result, decision.operator, scenario)
        control = control_by_zone.get(str(decision.zone_id), {})
        height_limit = float(control.get("height_limit_m", math.inf))
        spec = operator_specs[decision.operator]

        step_targets: dict[Any, float] = {}
        if decision.operator == "heritage_step_down":
            parameters = spec.get("parameters", {})
            influence = float(parameters.get("influence_distance_m", 80.0))
            maximum_shift = float(parameters.get("maximum_height_redistribution_ratio", 0.30))
            sensitive = baseline[
                baseline["heritage"].fillna(False)
                | baseline["residential_proxy"].fillna(False)
            ]
            if not sensitive.empty:
                sensitive_union = unary_union(list(sensitive.geometry))
                indices = list(result.index[eligible])
                distance_scores = {
                    index: min(
                        float(result.at[index, "geometry"].centroid.distance(sensitive_union))
                        / max(influence, 1e-6),
                        1.0,
                    )
                    for index in indices
                }
                if indices and max(distance_scores.values()) - min(distance_scores.values()) > 1e-9:
                    raw = {
                        index: 1.0 + maximum_shift * intensity * distance_scores[index]
                        for index in indices
                    }
                    before_total = sum(
                        float(result.at[index, "geometry"].area)
                        * float(result.at[index, "height_m"])
                        for index in indices
                    )
                    raw_total = sum(
                        float(result.at[index, "geometry"].area)
                        * float(result.at[index, "height_m"]) * raw[index]
                        for index in indices
                    )
                    normalizer = before_total / raw_total if raw_total > 0 else 1.0
                    step_targets = {
                        index: float(result.at[index, "height_m"]) * raw[index] * normalizer
                        for index in indices
                    }

        densify_targets: dict[Any, float] = {}
        densify_scale = 1.0
        available_gfa_m2 = math.inf
        requested_gfa_m2 = 0.0
        if decision.operator == "densify":
            gain = float(spec.get("parameters", {}).get("maximum_height_gain_ratio", 0.30))
            for index in result.index[eligible]:
                before_h = float(result.at[index, "height_m"])
                effective_cap = max(before_h, height_limit)
                densify_targets[index] = min(
                    before_h * (1.0 + gain * intensity), effective_cap
                )
                requested_gfa_m2 += (
                    float(result.at[index, "geometry"].area)
                    * max(densify_targets[index] - before_h, 0.0)
                    / FLOOR_HEIGHT_M
                )

            zone_area = area_by_zone.get(str(decision.zone_id))
            max_far = pd.to_numeric(control.get("max_far"), errors="coerce")
            if zone_area is not None and zone_area > 0 and pd.notna(max_far):
                zone_rows = result[zone_mask]
                current_gfa = float(
                    (zone_rows.geometry.area * zone_rows["height_m"] / FLOOR_HEIGHT_M).sum()
                )
                current_far = current_gfa / zone_area
                # Preserve legacy non-conformity, but never add to it.
                allowed_far = max(float(max_far), current_far)
                available_gfa_m2 = max(allowed_far * zone_area - current_gfa, 0.0)
                if requested_gfa_m2 > 0:
                    densify_scale = min(1.0, available_gfa_m2 / requested_gfa_m2)

        for index in result.index[eligible]:
            before_geom = result.at[index, "geometry"]
            before_h = float(result.at[index, "height_m"])
            after_geom = before_geom
            after_h = before_h

            if decision.operator == "densify":
                requested_height = densify_targets[index]
                after_h = before_h + (requested_height - before_h) * densify_scale
            elif decision.operator == "open_ground":
                minimum_ratio = float(spec.get("parameters", {}).get("minimum_footprint_ratio", 0.75))
                requested_ratio = 1.0 - intensity * (1.0 - minimum_ratio)
                scale = math.sqrt(max(requested_ratio, 1e-6))
                scaled = affinity.scale(before_geom, xfact=scale, yfact=scale, origin="centroid")
                # A centroid-scaled concave polygon can protrude outside its source.
                # Clipping makes "release ground" a true subset operation.
                clipped = scaled.intersection(before_geom)
                after_geom = clipped if not clipped.is_empty and clipped.area > 1e-6 else before_geom
                actual_ratio = float(after_geom.area / before_geom.area)
                if spec.get("parameters", {}).get("compensate_gfa", True):
                    effective_cap = max(before_h, height_limit)
                    after_h = min(before_h / max(actual_ratio, 1e-6), effective_cap)
            elif decision.operator == "split_to_towers":
                parameters = spec.get("parameters", {})
                minimum_area = float(parameters.get("minimum_building_area_m2", 300.0))
                if before_geom.area >= minimum_area:
                    maximum_gap = float(parameters.get("maximum_gap_ratio", 0.08))
                    after_geom = _split_with_central_gap(
                        before_geom, maximum_gap * intensity
                    )
                    actual_ratio = float(after_geom.area / before_geom.area)
                    if parameters.get("compensate_gfa", True):
                        effective_cap = max(before_h, height_limit)
                        after_h = min(before_h / max(actual_ratio, 1e-6), effective_cap)
            elif decision.operator == "heritage_step_down":
                after_h = min(step_targets.get(index, before_h), max(before_h, height_limit))
            elif decision.operator == "public_space_reconfiguration":
                parameters = spec.get("parameters", {})
                minimum_ratio = float(parameters.get("minimum_footprint_ratio", 0.90))
                maximum_depth = float(parameters.get("maximum_setback_depth_m", 4.0))
                if street_union is not None:
                    after_geom = _limited_cut(
                        before_geom,
                        lambda scale: _street_facing_setback_cutter(
                            before_geom,
                            street_union,
                            maximum_depth * intensity * scale,
                        ),
                        minimum_ratio,
                    )
            elif decision.operator == "courtyard_access_improvement":
                parameters = spec.get("parameters", {})
                minimum_ratio = float(parameters.get("minimum_footprint_ratio", 0.92))
                maximum_width = float(parameters.get("maximum_corridor_width_m", 3.0))
                if street_union is not None:
                    road_point, _ = nearest_points(street_union, before_geom.centroid)
                    _, entry = nearest_points(road_point, before_geom)
                    corridor_axis = LineString([entry, before_geom.centroid])
                    after_geom = _limited_cut(
                        before_geom,
                        lambda scale: corridor_axis.buffer(
                            maximum_width * intensity * scale / 2,
                            cap_style=2,
                            join_style=2,
                        ),
                        minimum_ratio,
                    )
            else:
                raise NotImplementedError(f"算子尚未实现：{decision.operator}")

            footprint_change_m2 = abs(float(after_geom.area - before_geom.area))
            height_change_m = abs(after_h - before_h)
            before_gfa_m2 = float(before_geom.area) * before_h / FLOOR_HEIGHT_M
            after_gfa_m2 = float(after_geom.area) * after_h / FLOOR_HEIGHT_M
            gfa_change_m2 = abs(after_gfa_m2 - before_gfa_m2)
            effective_change = (
                footprint_change_m2 >= minimum_footprint_change
                or height_change_m >= minimum_height_change
                or gfa_change_m2 >= minimum_gfa_change
            )
            if not effective_change:
                continue
            result.at[index, "geometry"] = after_geom
            result.at[index, "height_m"] = after_h
            result.at[index, "applied_operator"] = decision.operator
            result.at[index, "operator_intensity"] = intensity
            changes.append({
                "bid": str(result.at[index, "bid"]),
                "zone_id": str(decision.zone_id),
                "operator": decision.operator,
                "intensity": intensity,
                "before_height_m": before_h,
                "after_height_m": after_h,
                "before_area_m2": float(before_geom.area),
                "after_area_m2": float(after_geom.area),
                "footprint_change_m2": footprint_change_m2,
                "gfa_change_m2": float(after_gfa_m2 - before_gfa_m2),
                "requested_height_m": float(densify_targets[index])
                if decision.operator == "densify" else before_h,
                "capacity_allocation_ratio": float(densify_scale)
                if decision.operator == "densify" else 1.0,
                "zone_available_gfa_m2": float(available_gfa_m2)
                if decision.operator == "densify" and math.isfinite(available_gfa_m2) else None,
                "zone_requested_gfa_m2": float(requested_gfa_m2)
                if decision.operator == "densify" else None,
            })
    return result, changes

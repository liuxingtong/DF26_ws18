from __future__ import annotations

import math
from typing import Any

import geopandas as gpd
import pandas as pd
from shapely import affinity

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
) -> dict[str, tuple[str, ...]]:
    """Return operators that can produce a non-zero change in each zone."""
    control_by_zone = _control_map(controls)
    area_by_zone = _zone_area_map(zones)
    availability: dict[str, tuple[str, ...]] = {}
    for zone_id in zones["zone_id"].astype(str):
        zone_rows = baseline[baseline["zone_id"].astype(str).eq(zone_id)]
        allowed = ["noop"]
        open_ground_eligible = zone_rows[_eligible_for_operator(zone_rows, "open_ground", scenario)]
        if not open_ground_eligible.empty:
            allowed.append("open_ground")
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
        availability[zone_id] = tuple(allowed)
    return availability


def build_operator_impact_counts(
    baseline: gpd.GeoDataFrame,
    zones: gpd.GeoDataFrame,
    controls: pd.DataFrame | None,
    scenario: dict[str, Any] | None = None,
) -> dict[tuple[str, str], int]:
    """Conservative count of buildings an active operator can modify."""
    availability = build_operator_availability(baseline, zones, controls, scenario)
    control_by_zone = _control_map(controls)
    impacts: dict[tuple[str, str], int] = {}
    for zone_id in zones["zone_id"].astype(str):
        zone_rows = baseline[baseline["zone_id"].astype(str).eq(zone_id)]
        open_eligible = zone_rows[_eligible_for_operator(zone_rows, "open_ground", scenario)]
        densify_eligible = zone_rows[_eligible_for_operator(zone_rows, "densify", scenario)]
        impacts[(zone_id, "noop")] = 0
        impacts[(zone_id, "open_ground")] = (
            int(len(open_eligible)) if "open_ground" in availability[zone_id] else 0
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


def apply_decisions(
    baseline: gpd.GeoDataFrame,
    decisions: list[ZoneDecision],
    controls: pd.DataFrame | None,
    operator_specs: dict[str, Any],
    zones: gpd.GeoDataFrame | None = None,
    scenario: dict[str, Any] | None = None,
    minimum_change: dict[str, float] | None = None,
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

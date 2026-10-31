from __future__ import annotations

from functools import lru_cache
import math
from pathlib import Path

import geopandas as gpd
import pandas as pd
import yaml

from .models import ConstraintViolation


FLOOR_HEIGHT_M = 3.5
NEW_OVERLAP_TOLERANCE_M2 = 0.5
CONSTRAINT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "optimization" / "constraints.yaml"


@lru_cache(maxsize=1)
def constraint_policy() -> dict[str, dict]:
    payload = yaml.safe_load(CONSTRAINT_CONFIG_PATH.read_text(encoding="utf-8")) or {}
    return payload.get("constraints", {})


def _rule(code: str) -> dict:
    for rule in constraint_policy().values():
        if rule.get("violation_code") == code:
            return rule
    raise KeyError(f"constraints.yaml 未登记违规代码：{code}")


def _violation(code: str, message: str, **kwargs) -> ConstraintViolation:
    rule = _rule(code)
    return ConstraintViolation(
        code,
        message,
        severity=str(rule.get("severity", "blocking")),
        action=str(rule.get("handling", "reject_candidate")),
        **kwargs,
    )


def _new_overlap_violations(
    baseline: gpd.GeoDataFrame,
    candidate: gpd.GeoDataFrame,
) -> list[ConstraintViolation]:
    """Report overlap added by the proposal, while tolerating legacy overlap."""
    violations: list[ConstraintViolation] = []
    base_by_id = baseline.set_index("bid")
    candidate = candidate.reset_index(drop=True)
    changed_indices = []
    all_changed_footprints_are_subsets = True
    for index, row in candidate.iterrows():
        bid = row["bid"]
        if bid not in base_by_id.index or not base_by_id.loc[bid].geometry.equals_exact(row.geometry, 1e-7):
            changed_indices.append(index)
            if bid not in base_by_id.index or not base_by_id.loc[bid].geometry.covers(row.geometry):
                all_changed_footprints_are_subsets = False
    if not changed_indices:
        return violations
    # open_ground only shrinks footprints. A subset operation cannot introduce
    # overlap that was absent from the baseline, so the pairwise scan is unnecessary.
    if all_changed_footprints_are_subsets:
        return violations

    seen: set[tuple[str, str]] = set()
    spatial_index = candidate.sindex
    for index in changed_indices:
        row = candidate.iloc[index]
        bid = str(row["bid"])
        for other_index in spatial_index.query(row.geometry, predicate="intersects"):
            if int(other_index) == index:
                continue
            other = candidate.iloc[int(other_index)]
            other_bid = str(other["bid"])
            pair = tuple(sorted((bid, other_bid)))
            if pair in seen:
                continue
            seen.add(pair)
            new_area = float(row.geometry.intersection(other.geometry).area)
            old_area = 0.0
            if row["bid"] in base_by_id.index and other["bid"] in base_by_id.index:
                old_area = float(
                    base_by_id.loc[row["bid"]].geometry.intersection(
                        base_by_id.loc[other["bid"]].geometry
                    ).area
                )
            added = new_area - old_area
            tolerance = float(
                _rule("new_overlap").get(
                    "added_area_tolerance_m2", NEW_OVERLAP_TOLERANCE_M2
                )
            )
            if added > tolerance:
                violations.append(_violation(
                    "new_overlap",
                    f"建筑与 {other_bid} 新增重叠 {added:.2f} m²",
                    bid=bid,
                    value=added,
                    limit=tolerance,
                ))
    return violations


def check_constraints(
    baseline: gpd.GeoDataFrame,
    candidate: gpd.GeoDataFrame,
    boundary: gpd.GeoDataFrame,
    zones: gpd.GeoDataFrame | None,
    controls: pd.DataFrame | None,
    scenario: dict,
) -> list[ConstraintViolation]:
    violations: list[ConstraintViolation] = []
    study_geom = boundary.geometry.union_all()
    tolerance = float(_rule("boundary").get("tolerance_m", 0.05))

    base_by_id = baseline.set_index("bid")
    changed_count = 0
    for _, row in candidate.iterrows():
        geom = row.geometry
        bid = str(row["bid"])
        if geom is None or geom.is_empty or not geom.is_valid or geom.area <= 0:
            violations.append(_violation("geometry", "无效或空建筑几何", bid=bid))
            continue
        old = base_by_id.loc[row["bid"]] if row["bid"] in base_by_id.index else None
        if old is None or (not old.geometry.equals_exact(geom, tolerance=1e-7)
                           or abs(float(old["height_m"]) - float(row["height_m"])) > 1e-7):
            changed_count += 1
        old_inside = old is not None and study_geom.buffer(tolerance).covers(old.geometry)
        new_inside = study_geom.buffer(tolerance).covers(geom)
        # Report newly introduced boundary violations. Legacy edge mismatch is audited separately.
        if old_inside and not new_inside:
            violations.append(_violation("boundary", "建筑超出研究边界", bid=bid))

    maximum_changed_ratio = float(
        scenario.get("implementation", {}).get("maximum_changed_building_ratio", 1.0)
    )
    changed_ratio = changed_count / len(baseline) if len(baseline) else 0.0
    if changed_ratio > maximum_changed_ratio + 1e-9:
        violations.append(_violation(
            "change_scope",
            "发生形态变化的建筑比例超过情景范围",
            value=changed_ratio,
            limit=maximum_changed_ratio,
        ))

    for _, row in candidate[candidate["heritage"].fillna(False)].iterrows():
        bid = row["bid"]
        if bid not in base_by_id.index:
            continue
        old = base_by_id.loc[bid]
        if (not old.geometry.equals_exact(row.geometry, tolerance=1e-7)
                or abs(float(old["height_m"]) - float(row["height_m"])) > 1e-7):
            violations.append(_violation("heritage", "保护对象发生形态变化", bid=str(bid)))

    if controls is not None:
        control_by_zone = controls.set_index(controls["zone_id"].astype(str))
        for _, row in candidate.iterrows():
            zone_id = str(row.get("zone_id"))
            if zone_id not in control_by_zone.index:
                continue
            limit = pd.to_numeric(control_by_zone.loc[zone_id].get("height_limit_m"), errors="coerce")
            old_height = float(base_by_id.loc[row["bid"], "height_m"])
            allowed = max(float(limit), old_height) if pd.notna(limit) else math.inf
            if float(row["height_m"]) > allowed + 1e-6:
                violations.append(_violation(
                    "height_limit", "建筑超过分区限高", zone_id=zone_id, bid=str(row["bid"]),
                    value=float(row["height_m"]), limit=allowed,
                ))

    if zones is not None and controls is not None:
        zone_geoms = zones.set_index(zones["zone_id"].astype(str)).geometry
        control_by_zone = controls.set_index(controls["zone_id"].astype(str))
        base_grouped = {
            str(zone_id): subset for zone_id, subset in
            baseline.dropna(subset=["zone_id"]).groupby(baseline.dropna(subset=["zone_id"])["zone_id"].astype(str))
        }
        candidate_with_zone = candidate.dropna(subset=["zone_id"])
        for zone_id, subset in candidate_with_zone.groupby(candidate_with_zone["zone_id"].astype(str)):
            if zone_id not in zone_geoms.index or zone_id not in control_by_zone.index:
                continue
            zone_area = float(zone_geoms.loc[zone_id].area)
            if zone_area <= 0:
                continue
            footprint = float(subset.geometry.area.sum())
            gfa = float((subset.geometry.area * subset["height_m"] / FLOOR_HEIGHT_M).sum())
            far = gfa / zone_area
            coverage = footprint / zone_area
            max_far = pd.to_numeric(control_by_zone.loc[zone_id].get("max_far"), errors="coerce")
            max_cov = pd.to_numeric(control_by_zone.loc[zone_id].get("max_coverage_ratio"), errors="coerce")
            base_subset = base_grouped.get(zone_id)
            if base_subset is not None:
                base_far = float((base_subset.geometry.area * base_subset["height_m"] / FLOOR_HEIGHT_M).sum() / zone_area)
                base_coverage = float(base_subset.geometry.area.sum() / zone_area)
            else:
                base_far = base_coverage = 0.0
            allowed_far = max(float(max_far), base_far) if pd.notna(max_far) else math.inf
            allowed_coverage = max(float(max_cov), base_coverage) if pd.notna(max_cov) else math.inf
            if far > allowed_far + 1e-6:
                violations.append(_violation(
                    "zone_far", "更新单元新增或加重 FAR 违规", zone_id=zone_id, value=far, limit=allowed_far
                ))
            if coverage > allowed_coverage + 1e-6:
                violations.append(_violation(
                    "zone_coverage", "更新单元新增或加重覆盖率违规", zone_id=zone_id,
                    value=coverage, limit=allowed_coverage,
                ))

    base_res = baseline[baseline["residential_proxy"].fillna(False)]
    cand_res = candidate[candidate["residential_proxy"].fillna(False)]
    base_gfa = float((base_res.geometry.area * base_res["height_m"] / FLOOR_HEIGHT_M).sum())
    cand_gfa = float((cand_res.geometry.area * cand_res["height_m"] / FLOOR_HEIGHT_M).sum())
    retention = cand_gfa / base_gfa if base_gfa > 0 else 1.0
    minimum = float(scenario.get("defaults", {}).get("minimum_residential_retention", 0.80))
    if retention + 1e-9 < minimum:
        violations.append(_violation(
            "residential_retention", "住宅 GFA 保留率低于情景底线", value=retention, limit=minimum
        ))
    violations.extend(_new_overlap_violations(baseline, candidate))
    return violations

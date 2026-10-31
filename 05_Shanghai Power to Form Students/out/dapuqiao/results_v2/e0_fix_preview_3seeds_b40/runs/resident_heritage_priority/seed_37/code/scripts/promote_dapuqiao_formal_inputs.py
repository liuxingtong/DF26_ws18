#!/usr/bin/env python3
"""Promote reviewed Dapuqiao research inputs to frozen model-input files.

"Formal" here means the canonical input used by the paper experiments. It
does not mean cadastral, statutory planning, or legally surveyed data.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import date
from pathlib import Path

import geopandas as gpd
import pandas as pd


WS05 = Path(__file__).resolve().parents[1]
DATA = WS05 / "data" / "dapuqiao"
DRAFTS = DATA / "drafts"
REVIEW = WS05 / "review_app" / "public" / "data" / "review_cases.json"
REVIEW_MANIFEST = WS05 / "review_app" / "public" / "data" / "FREEZE_MANIFEST.json"
FREEZE_DATE = date(2026, 9, 27).isoformat()


def formal_zone_id(value: str) -> str:
    return value.replace("DRAFT_Z", "Z", 1)


def write_geojson(frame: gpd.GeoDataFrame, path: Path) -> None:
    path.write_text(
        frame.to_crs(4326).to_json(drop_id=True, ensure_ascii=False),
        encoding="utf-8",
    )


def build_zones() -> gpd.GeoDataFrame:
    zones = gpd.read_file(DRAFTS / "intervention_zones.draft.geojson").copy()
    zones["zone_id"] = zones["zone_id"].astype(str).map(formal_zone_id)
    zones["constraint_status"] = "research_assumption"
    zones["review_status"] = "frozen_research_input"
    zones["input_status"] = "formal_paper_model_input"
    zones["statutory_planning_unit"] = False
    zones["freeze_date"] = FREEZE_DATE
    zones["source"] = "OpenStreetMap-derived road enclosures; ODbL-1.0"
    write_geojson(zones, DATA / "intervention_zones.geojson")
    return zones


def build_controls(zones: gpd.GeoDataFrame) -> pd.DataFrame:
    controls = pd.read_csv(DRAFTS / "planning_controls.draft.csv").copy()
    controls["zone_id"] = controls["zone_id"].astype(str).map(formal_zone_id)
    controls["constraint_status"] = "research_assumption"
    controls["review_status"] = "frozen_research_input"
    controls["input_status"] = "formal_paper_model_input"
    controls["statutory_planning_control"] = False
    controls["freeze_date"] = FREEZE_DATE
    controls["source"] = "frozen paper-experiment baseline derived from existing form and shared defaults"
    controls["notes"] = (
        "Canonical research input; not a statutory control. Existing form is retained as a lower bound "
        "to avoid classifying the baseline as infeasible."
    )
    expected = set(zones["zone_id"].astype(str))
    actual = set(controls["zone_id"].astype(str))
    if actual != expected or controls["zone_id"].duplicated().any():
        raise ValueError("Planning-control keys do not match formal intervention zones one-to-one")
    controls.to_csv(DATA / "planning_controls.csv", index=False, encoding="utf-8-sig")
    return controls


def build_heritage(buildings: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    manifest = json.loads(REVIEW_MANIFEST.read_text(encoding="utf-8"))
    expected_review_hash = manifest.get("files", {}).get("review_cases.json")
    if expected_review_hash != sha256(REVIEW):
        raise ValueError("review_cases.json does not match its frozen SHA-256 manifest")
    reviews = json.loads(REVIEW.read_text(encoding="utf-8"))["reviews"]
    included = [row for row in reviews if row.get("include_in_optimization")]
    unresolved = [row for row in reviews if not row.get("include_in_optimization")]
    if len(included) != 12 or {row["id"] for row in unresolved} != {"HP-74", "HP-75", "HP-83", "HP-88"}:
        raise ValueError("Frozen review decision no longer matches the 12 included / 4 unresolved policy")

    by_bid: dict[str, list[dict]] = defaultdict(list)
    for row in included:
        for bid in row.get("suggested_bids", []):
            by_bid[str(bid)].append(row)
    if not by_bid:
        raise ValueError("No reviewed heritage building IDs were found")

    base = buildings.copy()
    base["bid"] = base["bid"].astype(str)
    heritage = base[base["bid"].isin(by_bid)].copy()
    missing = sorted(set(by_bid) - set(heritage["bid"]))
    if missing:
        raise ValueError(f"Reviewed heritage building IDs missing from buildings.parquet: {missing}")

    def joined(bid: str, field: str) -> str:
        return " | ".join(dict.fromkeys(str(row[field]) for row in by_bid[bid]))

    heritage["heritage"] = True
    heritage["editable"] = False
    heritage["heritage_record_ids"] = heritage["bid"].map(lambda bid: joined(bid, "id"))
    heritage["heritage_names"] = heritage["bid"].map(lambda bid: joined(bid, "name"))
    heritage["heritage_addresses"] = heritage["bid"].map(lambda bid: joined(bid, "address"))
    heritage["evidence_confidence"] = heritage["bid"].map(lambda bid: joined(bid, "evidence_confidence"))
    heritage["evidence_class"] = "official_record_plus_reviewed_geocoded_building_match"
    heritage["geometry_status"] = "preannotated_frozen"
    heritage["constraint_status"] = "formal_research_constraint"
    heritage["legal_boundary"] = False
    heritage["include_in_optimization"] = True
    heritage["review_status"] = "frozen_research_input"
    heritage["freeze_date"] = FREEZE_DATE
    heritage["source"] = included[0]["official_source"]
    keep = [
        "bid", "heritage", "editable", "heritage_record_ids", "heritage_names",
        "heritage_addresses", "evidence_confidence", "evidence_class", "geometry_status",
        "constraint_status", "legal_boundary", "include_in_optimization", "review_status",
        "freeze_date", "source", "geometry",
    ]
    heritage = heritage[keep].sort_values("bid").reset_index(drop=True)
    write_geojson(heritage, DATA / "heritage_buildings.geojson")
    return heritage


def overlap_area_m2(zones: gpd.GeoDataFrame) -> float:
    projected = zones.to_crs(32651).reset_index(drop=True)
    total = 0.0
    for left, geometry in projected.geometry.items():
        for right in projected.sindex.query(geometry, predicate="intersects"):
            if right <= left:
                continue
            total += geometry.intersection(projected.geometry.iloc[right]).area
    return float(total)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_quality(
    zones: gpd.GeoDataFrame,
    controls: pd.DataFrame,
    heritage: gpd.GeoDataFrame,
    buildings: gpd.GeoDataFrame,
) -> None:
    projected_buildings = buildings.to_crs(32651).copy()
    projected_zones = zones.to_crs(32651)
    points = projected_buildings[["bid", "geometry"]].copy()
    points["geometry"] = points.geometry.representative_point()
    joined = gpd.sjoin(points, projected_zones[["zone_id", "geometry"]], how="left", predicate="within")
    matched = int(joined.drop_duplicates("bid")["zone_id"].notna().sum())
    quality = {
        "freeze_date": FREEZE_DATE,
        "intended_use": "canonical paper-experiment model input",
        "statutory_or_cadastral": False,
        "counts": {
            "buildings": int(len(buildings)),
            "intervention_zones": int(len(zones)),
            "planning_control_rows": int(len(controls)),
            "heritage_building_footprints": int(len(heritage)),
            "heritage_official_records_represented": 12,
            "heritage_official_records_unresolved_and_excluded": 4,
            "buildings_matched_to_zones": matched,
            "buildings_unmatched_and_frozen": int(len(buildings) - matched),
        },
        "checks": {
            "zone_id_unique": bool(zones["zone_id"].is_unique),
            "zone_geometry_valid": bool(zones.geometry.is_valid.all()),
            "zone_pairwise_overlap_area_m2": round(overlap_area_m2(zones), 6),
            "controls_one_to_one_with_zones": set(controls["zone_id"].astype(str)) == set(zones["zone_id"].astype(str)),
            "control_ids_unique": bool(controls["zone_id"].is_unique),
            "control_numeric_values_present": bool(controls[["height_limit_m", "max_far", "max_coverage_ratio"]].notna().all().all()),
            "heritage_bid_unique": bool(heritage["bid"].is_unique),
            "heritage_bids_exist_in_buildings": set(heritage["bid"].astype(str)).issubset(set(buildings["bid"].astype(str))),
            "unresolved_records_excluded": True,
        },
        "limitations": [
            "Intervention zones are reproducible OSM-derived road enclosures, not manually surveyed parcels.",
            "All 38 planning-control rows remain research assumptions and are not statutory control-plan values.",
            "Heritage geometry is a frozen building-level research match for 12 official records, not a legal protection boundary.",
            "Four unresolved heritage records remain in review_cases.json and are excluded from optimization.",
        ],
    }
    files = [
        DATA / "intervention_zones.geojson",
        DATA / "planning_controls.csv",
        DATA / "heritage_buildings.geojson",
    ]
    quality["sha256"] = {path.name: sha256(path) for path in files}
    (DATA / "formal_input_quality.json").write_text(
        json.dumps(quality, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    buildings = gpd.read_parquet(DATA / "buildings.parquet")
    if buildings.crs is None:
        buildings = buildings.set_crs(32651)
    buildings["bid"] = buildings["bid"].astype(str)
    zones = build_zones()
    controls = build_controls(zones)
    heritage = build_heritage(buildings)
    build_quality(zones, controls, heritage, buildings)
    print(json.dumps({
        "status": "formal_research_inputs_written",
        "zones": len(zones),
        "controls": len(controls),
        "heritage_footprints": len(heritage),
        "output": str(DATA),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

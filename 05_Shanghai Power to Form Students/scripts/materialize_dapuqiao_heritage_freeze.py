#!/usr/bin/env python3
"""Materialize the frozen Dapuqiao heritage review as an optimization layer.

The frozen review keeps all official records in its evidence database. This
script exports only records explicitly marked ``include_in_optimization`` and
never substitutes a nearest building for an unresolved historic extent.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import geopandas as gpd


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data" / "dapuqiao"
FREEZE_ROOT = ROOT / "review_app" / "public" / "data"
DEFAULT_OUTPUT = DATA_ROOT / "heritage_buildings.geojson"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_verified_freeze(freeze_root: Path) -> tuple[dict, dict]:
    manifest_path = freeze_root / "FREEZE_MANIFEST.json"
    review_path = freeze_root / "review_cases.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    reviews = json.loads(review_path.read_text(encoding="utf-8"))

    expected = manifest.get("files", {}).get("review_cases.json")
    actual = sha256(review_path)
    if not expected or actual != expected:
        raise ValueError(
            "review_cases.json does not match the frozen SHA-256 manifest; "
            "create a new reviewed freeze before materializing it"
        )
    if len(reviews.get("reviews", [])) != int(manifest.get("record_count", -1)):
        raise ValueError("review record count does not match FREEZE_MANIFEST.json")
    return manifest, reviews


def build_layer(buildings_path: Path, freeze_root: Path) -> gpd.GeoDataFrame:
    manifest, payload = load_verified_freeze(freeze_root)
    buildings = gpd.read_parquet(buildings_path).copy()
    buildings["bid"] = buildings["bid"].astype(str)
    building_ids = set(buildings["bid"])

    rows: list[dict] = []
    missing: dict[str, list[str]] = {}
    included_records = 0
    for review in payload["reviews"]:
        if not review.get("include_in_optimization", False):
            continue
        included_records += 1
        bids = [str(bid) for bid in review.get("suggested_bids", [])]
        unknown = sorted(set(bids) - building_ids)
        if unknown:
            missing[str(review["id"])] = unknown
            continue
        if not bids:
            raise ValueError(
                f"{review['id']} is included in optimization but has no selected building"
            )
        for bid in bids:
            rows.append({
                "bid": bid,
                "heritage_record_id": str(review["id"]),
                "heritage_name": str(review["name"]),
                "official_address": str(review["address"]),
                "official_source": str(review["official_source"]),
                "evidence_confidence": str(review["evidence_confidence"]),
                "spatial_status": str(review["spatial_status"]),
                "freeze_id": str(manifest["freeze_id"]),
                "freeze_included_record_count": int(manifest["included_in_optimization"]),
                "freeze_unresolved_record_count": int(manifest["excluded_from_optimization"]),
                "constraint_status": "frozen_research_annotation",
                "include_in_optimization": True,
            })

    if missing:
        raise ValueError(f"frozen review references unknown building IDs: {missing}")
    expected_included = int(manifest.get("included_in_optimization", -1))
    if included_records != expected_included:
        raise ValueError(
            f"included record count {included_records} does not match manifest {expected_included}"
        )

    records = gpd.GeoDataFrame(rows)
    layer = records.merge(
        buildings[["bid", "geometry"]], on="bid", how="left", validate="many_to_one"
    )
    layer = gpd.GeoDataFrame(layer, geometry="geometry", crs=buildings.crs)
    if layer.empty or layer.geometry.isna().any():
        raise ValueError("materialized heritage layer contains missing geometry")
    return layer


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create the optimization heritage layer from the frozen review snapshot."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    layer = build_layer(DATA_ROOT / "buildings.parquet", FREEZE_ROOT)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    layer.to_file(args.output, driver="GeoJSON")
    print(json.dumps({
        "output": str(args.output),
        "heritage_buildings": len(layer),
        "official_records": int(layer["heritage_record_id"].nunique()),
        "freeze_id": str(layer["freeze_id"].iloc[0]),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

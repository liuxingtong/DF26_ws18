#!/usr/bin/env python3
"""Build reviewable Dapuqiao intervention-zone and control drafts.

The zones are road-corridor subtraction polygons derived from OpenStreetMap.
They are reproducible research drafts, not cadastral parcels or statutory
planning units. Review them in GIS before copying/renaming them to the formal
input filenames expected by the optimizer.
"""

from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
from shapely.ops import unary_union


WS05 = Path(__file__).resolve().parents[1]
DATA = WS05 / "data" / "dapuqiao"
OUTPUT = DATA / "drafts"
TARGET_CRS = 32651
MIN_ZONE_AREA_M2 = 5_000.0
ROAD_WIDTH_M = {
    "trunk": 14.0,
    "trunk_link": 10.0,
    "primary": 12.0,
    "primary_link": 8.0,
    "secondary": 10.0,
    "tertiary": 8.0,
    "residential": 5.0,
    "service": 3.0,
    "footway": 2.0,
    "steps": 2.0,
}
# These three road-bounded draft zones fall inside the official Tianzifang
# management extent: Sinan Rd / Ruijin 2nd Rd / Taikang Rd / Jianguo Middle Rd.
# The entire extent is frozen as a conservative proxy until the official
# building-by-building heritage list can be geocoded and reviewed.
TIANZIFANG_PROXY_ZONES = {"DRAFT_Z12", "DRAFT_Z13", "DRAFT_Z17"}


def read_layer(path: Path) -> gpd.GeoDataFrame:
    frame = gpd.read_file(path)
    if frame.crs is None:
        frame = frame.set_crs(4326)
    return frame.to_crs(TARGET_CRS)


def build_zones(boundary: gpd.GeoDataFrame, streets: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    road_corridors = []
    for _, road in streets.iterrows():
        width = ROAD_WIDTH_M.get(road.get("highway"), 3.0)
        road_corridors.append(road.geometry.buffer(width / 2.0, cap_style=2, join_style=2))
    buildable_fabric = boundary.geometry.union_all().difference(unary_union(road_corridors))
    parts = list(buildable_fabric.geoms) if buildable_fabric.geom_type == "MultiPolygon" else [buildable_fabric]
    large_parts = [part for part in parts if not part.is_empty and part.area >= MIN_ZONE_AREA_M2]
    small_parts = [part for part in parts if not part.is_empty and 10.0 < part.area < MIN_ZONE_AREA_M2]
    # Keep a reviewable 20–40 zone count without discarding dense small blocks.
    # Small road-separated fragments are attached to their nearest large draft zone.
    for small in sorted(small_parts, key=lambda geometry: geometry.area, reverse=True):
        nearest = min(range(len(large_parts)), key=lambda index: small.distance(large_parts[index]))
        large_parts[nearest] = large_parts[nearest].union(small)
    parts = sorted(
        large_parts,
        key=lambda geometry: (geometry.centroid.y, geometry.centroid.x),
        reverse=True,
    )
    return gpd.GeoDataFrame(
        [{
            "zone_id": f"DRAFT_Z{index:02d}",
            "zone_method": "osm_road_corridor_subtraction_small_fragments_merged",
            "constraint_status": "research_assumption",
            "review_status": "needs_manual_gis_review",
            "source": "OpenStreetMap-derived roads; ODbL-1.0",
            "geometry": geometry,
        } for index, geometry in enumerate(parts, start=1)],
        geometry="geometry",
        crs=boundary.crs,
    )


def assign_buildings(buildings: gpd.GeoDataFrame, zones: gpd.GeoDataFrame) -> pd.DataFrame:
    points = buildings[["bid", "geometry"]].copy()
    points["geometry"] = points.geometry.representative_point()
    joined = gpd.sjoin(points, zones[["zone_id", "geometry"]], how="left", predicate="within")
    return joined[["bid", "zone_id"]].drop_duplicates("bid")


def build_controls(
    buildings: gpd.GeoDataFrame,
    zones: gpd.GeoDataFrame,
    assignments: pd.DataFrame,
) -> pd.DataFrame:
    joined = buildings.merge(assignments, on="bid", how="left")
    zone_areas = zones.set_index("zone_id").geometry.area
    rows = []
    for zone_id, zone in zones.set_index("zone_id").iterrows():
        subset = joined[joined["zone_id"].eq(zone_id)]
        area = float(zone_areas.loc[zone_id])
        footprint = float(subset.geometry.area.sum()) if len(subset) else 0.0
        gfa = float((subset.geometry.area * subset["height_m"] / 3.5).sum()) if len(subset) else 0.0
        existing_far = gfa / area if area > 0 else 0.0
        existing_coverage = footprint / area if area > 0 else 0.0
        existing_height = float(subset["height_m"].max()) if len(subset) else 0.0
        rows.append({
            "zone_id": zone_id,
            "existing_buildings": int(len(subset)),
            "existing_far": round(existing_far, 4),
            "existing_coverage_ratio": round(existing_coverage, 4),
            "existing_max_height_m": round(existing_height, 2),
            "height_limit_m": round(max(existing_height, 36.0), 2),
            "max_far": round(max(existing_far, 3.0), 4),
            "max_coverage_ratio": round(max(existing_coverage, 0.60), 4),
            "allow_new_building": True,
            "constraint_status": "research_assumption",
            "source": "auto draft from existing form and scenario defaults; manual review required",
            "notes": "Do not treat as statutory planning control.",
        })
    return pd.DataFrame(rows)


def build_heritage_proxy(
    buildings: gpd.GeoDataFrame,
    assignments: pd.DataFrame,
) -> gpd.GeoDataFrame:
    assigned = buildings.merge(assignments, on="bid", how="left")
    proxy = assigned[assigned["zone_id"].isin(TIANZIFANG_PROXY_ZONES)].copy()
    proxy["heritage_proxy"] = True
    proxy["proxy_name"] = "Tianzifang conservative protection proxy"
    proxy["evidence_class"] = "official_extent_plus_conservative_research_assumption"
    proxy["official_extent"] = "E Sinan Rd; W Ruijin 2nd Rd; S Taikang Rd; N Jianguo Middle Rd"
    proxy["source_document"] = "Huangpu Government Regulation [2023] No. 3"
    proxy["review_status"] = "building_level_official_list_not_yet_matched"
    return proxy[[
        "bid", "zone_id", "heritage_proxy", "proxy_name", "evidence_class",
        "official_extent", "source_document", "review_status", "geometry",
    ]]


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    buildings = gpd.read_parquet(DATA / "buildings.parquet")
    if buildings.crs is None:
        buildings = buildings.set_crs(TARGET_CRS)
    buildings = buildings.to_crs(TARGET_CRS)
    buildings["bid"] = buildings["bid"].astype(str) if "bid" in buildings else [
        f"B_{index:05d}" for index in range(len(buildings))
    ]
    boundary = read_layer(DATA / "study_boundary.geojson")
    streets = read_layer(DATA / "street_network.geojson")
    zones = build_zones(boundary, streets)
    assignments = assign_buildings(buildings, zones)
    controls = build_controls(buildings, zones, assignments)
    heritage_proxy = build_heritage_proxy(buildings, assignments)

    (OUTPUT / "intervention_zones.draft.geojson").write_text(
        zones.to_crs(4326).to_json(drop_id=True, ensure_ascii=False), encoding="utf-8"
    )
    controls.to_csv(OUTPUT / "planning_controls.draft.csv", index=False, encoding="utf-8-sig")
    assignments.to_csv(OUTPUT / "building_zone_assignment.draft.csv", index=False, encoding="utf-8-sig")
    (OUTPUT / "heritage_buildings.draft.geojson").write_text(
        heritage_proxy.to_crs(4326).to_json(drop_id=True, ensure_ascii=False), encoding="utf-8"
    )
    assigned = buildings.merge(assignments, on="bid", how="left")
    figure, axis = plt.subplots(figsize=(10, 8))
    zones.plot(ax=axis, column="zone_id", cmap="tab20", alpha=0.35, edgecolor="#444444", linewidth=0.5)
    streets.plot(ax=axis, color="#777777", linewidth=0.35, alpha=0.6)
    buildings.boundary.plot(ax=axis, color="#222222", linewidth=0.18, alpha=0.45)
    unmatched = assigned[assigned["zone_id"].isna()].copy()
    if len(unmatched):
        unmatched["geometry"] = unmatched.geometry.representative_point()
        unmatched.plot(ax=axis, color="#d73027", markersize=6, label="Unmatched buildings")
        axis.legend(loc="lower left")
    boundary.boundary.plot(ax=axis, color="#111111", linewidth=1.2)
    axis.set_title("Dapuqiao draft intervention zones — manual GIS review required")
    axis.set_axis_off()
    figure.tight_layout()
    figure.savefig(OUTPUT / "draft_preview.png", dpi=180, bbox_inches="tight")
    plt.close(figure)
    matched = int(assignments["zone_id"].notna().sum())
    summary = {
        "status": "research_draft_needs_manual_gis_review",
        "method": "OSM road corridors subtracted from the study boundary; fragments below 5,000 m² merged to the nearest large draft zone",
        "minimum_zone_area_m2": MIN_ZONE_AREA_M2,
        "zone_count": int(len(zones)),
        "building_count": int(len(buildings)),
        "matched_buildings": matched,
        "unmatched_buildings": int(len(buildings) - matched),
        "matched_building_ratio": round(matched / len(buildings), 6),
        "tianzifang_heritage_proxy_zones": sorted(TIANZIFANG_PROXY_ZONES),
        "tianzifang_heritage_proxy_buildings": int(len(heritage_proxy)),
        "road_width_m": ROAD_WIDTH_M,
        "formal_input_instructions": [
            "Review and edit zone boundaries in GIS.",
            "Resolve the unmatched-building list.",
            "Replace research assumptions with sourced controls where possible.",
            "Only after review, copy files to intervention_zones.geojson and planning_controls.csv.",
        ],
    }
    (OUTPUT / "draft_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

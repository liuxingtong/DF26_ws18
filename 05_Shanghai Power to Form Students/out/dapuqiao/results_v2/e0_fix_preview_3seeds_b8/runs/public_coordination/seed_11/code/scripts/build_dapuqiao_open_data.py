"""Build redistributable Dapuqiao research layers from OpenStreetMap.

Generated files are OSM-derived ODbL data. They are research inputs, not
official planning, cadastral, heritage, ownership, or access determinations.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests
import yaml
from shapely.geometry import LineString, Point, Polygon, shape


PLACE_QUERY = "打浦桥街道, 黄浦区, 上海市, 中国"
OSM_RELATION = 12235958
CRS = "EPSG:4326"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
USER_AGENT = "DF26_ws18-research-data/1.0 (https://github.com/liuxingtong/DF26_ws18)"
SELECTED_OVERPASS_URL: str | None = None

SERVICE_AMENITIES = {
    "school",
    "kindergarten",
    "college",
    "university",
    "hospital",
    "clinic",
    "doctors",
    "pharmacy",
    "social_facility",
    "community_centre",
    "marketplace",
}

PUBLIC_SPACE_VERIFICATION = {
    1209934031: {
        "research_status": "candidate_unverified_excluded",
        "verification_date": "2026-09-28",
        "verification_method": "OSM tag plus AMap nearby-POI cross-check",
        "verification_sources": "https://www.openstreetmap.org/way/1209934031",
        "amap_match": False,
        "amap_poi_id": None,
        "address_verified": None,
        "official_reported_area_m2": None,
        "official_reported_green_area_m2": None,
        "official_area_reference_year": None,
        "public_access_evidence": "not_verified",
        "ownership_status": "not_verified",
        "legal_boundary": False,
        "include_in_public_space_context": False,
        "include_in_objective": False,
        "verification_note": (
            "No same-name AMap public-space POI was returned near this coordinate; "
            "multiple unrelated Shanghai places share the name. Keep frozen and excluded."
        ),
    },
    72083112: {
        "research_status": "verified_public_park_context",
        "verification_date": "2026-09-28",
        "verification_method": (
            "OSM tag, AMap POI, Huangpu statistical yearbook and Shanghai "
            "park-management evidence"
        ),
        "verification_sources": (
            "https://www.openstreetmap.org/way/72083112 | "
            "https://www.shhuangpu.gov.cn/uploadfile/"
            "de2d24bb-b3a2-4ac8-a4f5-5e15bc8fa8bf/"
            "2014%E5%B9%B4%E9%BB%84%E6%B5%A6%E7%BB%9F%E8%AE%A1%E5%B9%B4%E9%89%B4.pdf | "
            "https://lhsr.sh.gov.cn/cmsres/99/"
            "99d8041e933d40259d86d3a556daeb12/"
            "051e89e66f8b0d8cfa9e00e63822dbfc.pdf | "
            "https://lhsr.sh.gov.cn/ywdt/20250915/c44b20ec-3822-4053-a336-65f2cd27a29b.html"
        ),
        "amap_match": True,
        "amap_poi_id": "B00155HQDA",
        "address_verified": "上海市黄浦区丽园路565号",
        "official_reported_area_m2": 17460,
        "official_reported_green_area_m2": 11131,
        "official_area_reference_year": 2013,
        "public_access_evidence": "official_park_listing_and_public_opening_program",
        "official_opening_hours_last_published": "05:00-21:00",
        "official_opening_hours_reference_year": 2021,
        "opening_hours_status": "historical_official_schedule; current_hours_not_reverified",
        "ownership_status": "not_verified",
        "legal_boundary": False,
        "include_in_public_space_context": True,
        "include_in_objective": False,
        "verification_note": (
            "Official sources support public-park identity and a 2021 published schedule. "
            "The OSM polygon is research geometry only; historical area and OSM geometry "
            "are not a current surveyed or legal boundary, and current hours remain unverified."
        ),
    },
}


def parse_args() -> argparse.Namespace:
    default_output = Path(__file__).resolve().parents[1] / "data" / "dapuqiao"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=default_output)
    parser.add_argument(
        "--public-spaces-only", action="store_true",
        help="只刷新公共空间 OSM 几何与对应质量/来源元数据",
    )
    return parser.parse_args()


def get_json(url: str, *, params: dict | None = None, data: dict | None = None) -> dict | list:
    response = requests.request(
        "POST" if data else "GET",
        url,
        params=params,
        data=data,
        headers={"User-Agent": USER_AGENT},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def boundary_layer() -> gpd.GeoDataFrame:
    results = get_json(
        NOMINATIM_URL,
        params={
            "q": PLACE_QUERY,
            "format": "jsonv2",
            "polygon_geojson": 1,
            "addressdetails": 1,
            "limit": 5,
        },
    )
    matches = [
        item
        for item in results
        if item.get("osm_type") == "relation" and int(item.get("osm_id", -1)) == OSM_RELATION
    ]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one OSM relation {OSM_RELATION}, found {len(matches)}")
    item = matches[0]
    geometry = shape(item["geojson"])
    return gpd.GeoDataFrame(
        [
            {
                "name": "打浦桥街道",
                "element_type": "relation",
                "osm_id": OSM_RELATION,
                "display_name": item["display_name"],
                "source": "OpenStreetMap",
                "license": "ODbL-1.0",
                "geometry": geometry,
            }
        ],
        crs=CRS,
    )


def overpass(query: str) -> tuple[list[dict], str | None]:
    global SELECTED_OVERPASS_URL
    if SELECTED_OVERPASS_URL:
        try:
            payload = get_json(SELECTED_OVERPASS_URL, data={"data": query})
            return payload["elements"], payload.get("osm3s", {}).get("timestamp_osm_base")
        except (requests.RequestException, ValueError, KeyError) as exc:
            raise RuntimeError(
                f"Selected Overpass endpoint failed; rerun to select a new consistent snapshot: "
                f"{SELECTED_OVERPASS_URL}: {type(exc).__name__}: {exc}"
            ) from exc
    errors = []
    for url in OVERPASS_URLS:
        try:
            payload = get_json(url, data={"data": query})
            SELECTED_OVERPASS_URL = url
            return payload["elements"], payload.get("osm3s", {}).get("timestamp_osm_base")
        except (requests.RequestException, ValueError, KeyError) as exc:
            errors.append(f"{url}: {type(exc).__name__}: {exc}")
    raise RuntimeError("All Overpass endpoints failed:\n" + "\n".join(errors))


def point_geometry(element: dict) -> Point | None:
    if "lat" in element and "lon" in element:
        return Point(element["lon"], element["lat"])
    center = element.get("center")
    if center:
        return Point(center["lon"], center["lat"])
    return None


def way_geometry(element: dict) -> LineString | Polygon | None:
    coordinates = [(item["lon"], item["lat"]) for item in element.get("geometry", [])]
    if len(coordinates) < 2:
        return point_geometry(element)
    if len(coordinates) >= 4 and coordinates[0] == coordinates[-1]:
        return Polygon(coordinates)
    return LineString(coordinates)


def rows_to_gdf(elements: list[dict], *, preserve_way_geometry: bool) -> gpd.GeoDataFrame:
    rows = []
    for element in elements:
        geometry = (
            way_geometry(element)
            if preserve_way_geometry and element["type"] == "way"
            else point_geometry(element)
        )
        if geometry is None:
            continue
        row = dict(element.get("tags", {}))
        row.update(
            {
                "element_type": element["type"],
                "osm_id": int(element["id"]),
                "osm_version": element.get("version"),
                "osm_last_updated": element.get("timestamp"),
                "geometry": geometry,
            }
        )
        rows.append(row)
    result = gpd.GeoDataFrame(rows, crs=CRS)
    if len(result):
        result = result.drop_duplicates(["element_type", "osm_id"]).reset_index(drop=True)
    return result


def select_columns(frame: gpd.GeoDataFrame, columns: list[str]) -> gpd.GeoDataFrame:
    for column in columns:
        if column not in frame:
            frame[column] = None
    return frame[columns + ["geometry"]].copy()


def overpass_bbox(boundary: Polygon) -> str:
    min_lon, min_lat, max_lon, max_lat = boundary.bounds
    return f"{min_lat},{min_lon},{max_lat},{max_lon}"


def street_layer(boundary: Polygon) -> tuple[gpd.GeoDataFrame, str | None]:
    bbox = overpass_bbox(boundary)
    elements, timestamp = overpass(
        f"""[out:json][timeout:45];
        way[\"highway\"]({bbox});
        out geom tags;"""
    )
    streets = rows_to_gdf(elements, preserve_way_geometry=True)
    streets = streets[streets.geometry.geom_type.isin(["LineString", "MultiLineString"])]
    streets = gpd.clip(streets, boundary, keep_geom_type=True)
    streets["source"] = "OpenStreetMap"
    streets["license"] = "ODbL-1.0"
    return select_columns(
        streets,
        [
            "element_type", "osm_id", "name", "name:zh", "highway", "service",
            "surface", "access", "foot", "bicycle", "motor_vehicle", "oneway",
            "lanes", "width", "maxspeed", "source", "license",
        ],
    ), timestamp


def service_layer(boundary: Polygon) -> tuple[gpd.GeoDataFrame, str | None]:
    amenity_pattern = "|".join(sorted(SERVICE_AMENITIES))
    bbox = overpass_bbox(boundary)
    elements, timestamp = overpass(
        f"""[out:json][timeout:45];
        (
          nwr[\"amenity\"~\"^({amenity_pattern})$\"]({bbox});
          nwr[\"public_transport\"]({bbox});
          nwr[\"highway\"=\"bus_stop\"]({bbox});
          nwr[\"railway\"~\"^(station|halt|tram_stop|subway_entrance)$\"]({bbox});
        );
        out center tags;"""
    )
    services = rows_to_gdf(elements, preserve_way_geometry=False)
    services = services[services.geometry.within(boundary) | services.geometry.touches(boundary)]
    services["service_group"] = "other"
    groups = {
        "education": {"school", "kindergarten", "college", "university"},
        "healthcare": {"hospital", "clinic", "doctors", "pharmacy"},
        "social_service": {"social_facility", "community_centre"},
        "market": {"marketplace"},
    }
    for group, values in groups.items():
        services.loc[services.get("amenity", pd.Series(index=services.index)).isin(values), "service_group"] = group
    transit = pd.Series(False, index=services.index)
    if "public_transport" in services:
        transit |= services["public_transport"].notna()
    if "highway" in services:
        transit |= services["highway"].eq("bus_stop")
    if "railway" in services:
        transit |= services["railway"].isin(["station", "halt", "tram_stop", "subway_entrance"])
    services.loc[transit, "service_group"] = "public_transport"
    services["source"] = "OpenStreetMap"
    services["license"] = "ODbL-1.0"
    return select_columns(
        services,
        [
            "element_type", "osm_id", "name", "name:zh", "service_group", "amenity",
            "healthcare", "social_facility", "public_transport", "highway", "railway",
            "operator", "access", "wheelchair", "source", "license",
        ],
    ), timestamp


def public_space_layer(
    boundary: Polygon, *, known_candidates_only: bool = False
) -> tuple[gpd.GeoDataFrame, str | None]:
    bbox = overpass_bbox(boundary)
    if known_candidates_only:
        known_ids = ",".join(str(value) for value in PUBLIC_SPACE_VERIFICATION)
        query = f"[out:json][timeout:45];way(id:{known_ids});out meta geom;"
    else:
        query = f"""[out:json][timeout:45];
            (
              nwr[\"leisure\"~\"^(park|garden|playground|recreation_ground)$\"]({bbox});
              nwr[\"place\"=\"square\"]({bbox});
              nwr[\"landuse\"~\"^(recreation_ground|village_green)$\"]({bbox});
            );
            out meta geom;"""
    elements, timestamp = overpass(query)
    spaces = rows_to_gdf(elements, preserve_way_geometry=True)
    spaces = gpd.clip(spaces, boundary, keep_geom_type=False)
    metric = spaces.to_crs(spaces.estimate_utm_crs())
    spaces["osm_geometry_area_m2"] = metric.geometry.area.round(2).values
    spaces["source"] = "OpenStreetMap"
    spaces["license"] = "ODbL-1.0"
    spaces["research_status"] = "candidate_unverified_excluded"
    spaces["geometry_status"] = spaces.geometry.geom_type.map(
        lambda kind: "osm_polygon_research_geometry" if kind in {"Polygon", "MultiPolygon"}
        else "osm_way_represented_as_point; polygon_refresh_pending"
    )
    for osm_id, annotation in PUBLIC_SPACE_VERIFICATION.items():
        mask = spaces["osm_id"].eq(osm_id)
        for field, value in annotation.items():
            spaces.loc[mask, field] = value
    return select_columns(
        spaces,
        [
            "element_type", "osm_id", "osm_version", "osm_last_updated",
            "name", "name:zh", "leisure", "place",
            "landuse", "access", "opening_hours", "operator", "research_status",
            "verification_date", "verification_method", "verification_sources",
            "amap_match", "amap_poi_id", "address_verified",
            "official_reported_area_m2", "official_reported_green_area_m2",
            "official_area_reference_year", "public_access_evidence",
            "official_opening_hours_last_published",
            "official_opening_hours_reference_year", "opening_hours_status",
            "ownership_status", "geometry_status", "legal_boundary",
            "osm_geometry_area_m2",
            "include_in_public_space_context", "include_in_objective",
            "verification_note",
            "source", "license",
        ],
    ), timestamp


def write_geojson(frame: gpd.GeoDataFrame, path: Path) -> None:
    path.write_text(frame.to_json(drop_id=True, ensure_ascii=False), encoding="utf-8")


def quality_summary(layers: dict[str, gpd.GeoDataFrame]) -> dict:
    summary = {}
    for name, frame in layers.items():
        duplicate_keys = 0
        if {"element_type", "osm_id"}.issubset(frame.columns):
            duplicate_keys = int(frame.duplicated(["element_type", "osm_id"]).sum())
        item = {
            "features": int(len(frame)),
            "crs": str(frame.crs),
            "empty_geometries": int(frame.geometry.is_empty.sum()),
            "null_geometries": int(frame.geometry.isna().sum()),
            "invalid_geometries": int((~frame.geometry.is_valid).sum()),
            "duplicate_osm_keys": duplicate_keys,
            "geometry_types": sorted(frame.geometry.geom_type.unique().tolist()),
            "bounds": [round(float(value), 7) for value in frame.total_bounds],
        }
        if "name" in frame.columns:
            item["null_names"] = int(frame["name"].isna().sum())
            item["null_name_rate"] = round(float(frame["name"].isna().mean()), 6)
        if "research_status" in frame.columns:
            item["research_status_counts"] = {
                str(key): int(value)
                for key, value in frame["research_status"].fillna("missing").value_counts().items()
            }
        summary[name] = item
    return summary


def main() -> None:
    args = parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    if args.public_spaces_only:
        boundary_path = output / "study_boundary.geojson"
        if not boundary_path.exists():
            raise FileNotFoundError(f"缺少既有研究边界：{boundary_path}")
        boundary = gpd.read_file(boundary_path).to_crs(CRS)
        spaces, space_timestamp = public_space_layer(
            boundary.geometry.union_all(), known_candidates_only=True
        )
        write_geojson(spaces, output / "public_space_candidates.geojson")
        section = quality_summary({"public_space_candidates": spaces})[
            "public_space_candidates"
        ]
        section["included_in_objective"] = int(
            spaces["include_in_objective"].astype("boolean").fillna(False).sum()
        )
        section["verification_date"] = "2026-09-28"
        quality_path = output / "open_data_quality.json"
        quality = (
            json.loads(quality_path.read_text(encoding="utf-8"))
            if quality_path.exists() else {}
        )
        quality["public_space_candidates"] = section
        quality_path.write_text(
            json.dumps(quality, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        sources_path = output / "open_data_sources.yaml"
        sources = (
            yaml.safe_load(sources_path.read_text(encoding="utf-8")) or {}
            if sources_path.exists() else {}
        )
        sources["public_space_refreshed_at_utc"] = (
            datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        )
        sources["public_space_osm_base_timestamp"] = space_timestamp
        sources_path.write_text(
            yaml.safe_dump(sources, allow_unicode=True, sort_keys=False), encoding="utf-8"
        )
        print(json.dumps(section, ensure_ascii=False, indent=2))
        return

    boundary = boundary_layer()
    polygon = boundary.geometry.iloc[0]
    streets, street_timestamp = street_layer(polygon)
    services, service_timestamp = service_layer(polygon)
    spaces, space_timestamp = public_space_layer(polygon)
    layers = {
        "study_boundary": boundary,
        "street_network": streets,
        "public_services": services,
        "public_space_candidates": spaces,
    }
    for name, frame in layers.items():
        write_geojson(frame, output / f"{name}.geojson")

    quality = quality_summary(layers)
    boundary_area_km2 = float(
        boundary.to_crs(boundary.estimate_utm_crs()).geometry.area.iloc[0] / 1_000_000
    )
    metadata = {
        "dataset": "Dapuqiao Open Research Layers",
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "osm_base_timestamps": sorted(
            {value for value in [street_timestamp, service_timestamp, space_timestamp] if value}
        ),
        "overpass_endpoint": SELECTED_OVERPASS_URL,
        "place_query": PLACE_QUERY,
        "boundary_osm_relation": OSM_RELATION,
        "source": "OpenStreetMap contributors",
        "source_url": f"https://www.openstreetmap.org/relation/{OSM_RELATION}",
        "license": "ODbL-1.0",
        "license_url": "https://www.openstreetmap.org/copyright",
        "crs": CRS,
        "boundary_area_km2": round(boundary_area_km2, 6),
        "limitations": [
            "OpenStreetMap completeness and tags vary by feature and date.",
            "Only two public-space candidates were mapped in this OSM snapshot; coverage is incomplete.",
            "The OSM boundary area is about 0.86% smaller than the legacy local boundary used by site.yaml.",
            "Liyuan Park is verified only as a context-level public park; its current surveyed and legal boundary remains unverified.",
            "Baiyulan Square remains an unverified, excluded OSM candidate; its access and ownership are not established.",
            "These files are not official planning, cadastral, or heritage records.",
            "Alley entrances are not represented as a separately verified layer.",
        ],
        "quality": quality,
    }
    (output / "open_data_sources.yaml").write_text(
        yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    (output / "open_data_quality.json").write_text(
        json.dumps(quality, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(quality, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

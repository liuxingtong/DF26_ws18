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


def parse_args() -> argparse.Namespace:
    default_output = Path(__file__).resolve().parents[1] / "data" / "dapuqiao"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=default_output)
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


def public_space_layer(boundary: Polygon) -> tuple[gpd.GeoDataFrame, str | None]:
    bbox = overpass_bbox(boundary)
    elements, timestamp = overpass(
        f"""[out:json][timeout:45];
        (
          nwr[\"leisure\"~\"^(park|garden|playground|recreation_ground)$\"]({bbox});
          nwr[\"place\"=\"square\"]({bbox});
          nwr[\"landuse\"~\"^(recreation_ground|village_green)$\"]({bbox});
        );
        out geom center tags;"""
    )
    spaces = rows_to_gdf(elements, preserve_way_geometry=True)
    spaces = gpd.clip(spaces, boundary, keep_geom_type=False)
    spaces["source"] = "OpenStreetMap"
    spaces["license"] = "ODbL-1.0"
    spaces["research_status"] = "candidate_not_access_verified"
    return select_columns(
        spaces,
        [
            "element_type", "osm_id", "name", "name:zh", "leisure", "place",
            "landuse", "access", "opening_hours", "operator", "research_status",
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
        summary[name] = item
    return summary


def main() -> None:
    args = parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

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
            "Public-space access and ownership have not been field verified.",
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

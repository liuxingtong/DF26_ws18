"""Render the study-area diagram from frozen GeoJSON and the cached satellite image."""

import json
from pathlib import Path

from PIL import Image, ImageDraw
from pyproj import Transformer
from shapely.geometry import shape

from make_preview_pareto import font


ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "05_Shanghai Power to Form Students/data/dapuqiao"
GROUND = ROOT / "06_AI Render Students/out/dapuqiao"
OUTPUT = Path(__file__).with_name("study_area_satellite.png")
TRANSFORMER = Transformer.from_crs(4326, 32651, always_xy=True)
SCALE = 2
WIDTH, MAP_HEIGHT, FOOTER = 1600, 960, 88


def features(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))["features"]


def polygons(geometry):
    item = shape(geometry)
    if item.geom_type == "Polygon":
        return [item]
    if item.geom_type == "MultiPolygon":
        return list(item.geoms)
    return []


def draw():
    meta = json.loads((GROUND / "ground_scene.json").read_text(encoding="utf-8"))
    origin_x, origin_y = meta["bounds"][:2]
    west, south, east, north = meta["local"]
    photo = Image.open(GROUND / "ground_scene.jpg").convert("RGB")
    photo = photo.resize((WIDTH * SCALE, MAP_HEIGHT * SCALE), Image.Resampling.LANCZOS)
    veil = Image.new("RGB", photo.size, "white")
    photo = Image.blend(photo, veil, 0.23)
    image = Image.new("RGB", (WIDTH * SCALE, (MAP_HEIGHT + FOOTER) * SCALE), "white")
    image.paste(photo, (0, 0))
    ink = ImageDraw.Draw(image, "RGBA")

    def project(point):
        x, y = TRANSFORMER.transform(*point)
        return ((x - origin_x - west) / (east - west) * WIDTH * SCALE,
                (north - (y - origin_y)) / (north - south) * MAP_HEIGHT * SCALE)

    def outline(poly, fill, width):
        points = [project(point) for point in poly.exterior.coords]
        ink.line(points, fill=fill, width=width * SCALE, joint="curve")

    for feature in features("intervention_zones.geojson"):
        for polygon in polygons(feature["geometry"]):
            outline(polygon, (255, 255, 255, 210), 2)
            outline(polygon, (43, 75, 75, 150), 1)
    for feature in features("study_boundary.geojson"):
        for polygon in polygons(feature["geometry"]):
            outline(polygon, (255, 255, 255, 245), 7)
            outline(polygon, (18, 72, 74, 250), 4)
    for feature in features("heritage_buildings.geojson"):
        for polygon in polygons(feature["geometry"]):
            points = [project(point) for point in polygon.exterior.coords]
            ink.polygon(points, fill=(215, 91, 51, 235), outline=(255, 255, 255, 255))

    top_band = Image.new("RGBA", (WIDTH * SCALE, 102 * SCALE), (255, 255, 255, 220))
    image.paste(top_band, (0, 0), top_band)
    ink = ImageDraw.Draw(image)
    title = "Dapuqiao Study Area"
    ink.text((WIDTH * SCALE / 2, 49 * SCALE), title, font=font(30, True), fill="#111111", anchor="mm")
    ink.text((1514 * SCALE, 155 * SCALE), "N", font=font(18, True), fill="#111111", anchor="mm")
    ink.line(((1514 * SCALE, 172 * SCALE), (1514 * SCALE, 228 * SCALE)), fill="#111111", width=3 * SCALE)
    ink.polygon(((1514 * SCALE, 168 * SCALE), (1506 * SCALE, 184 * SCALE), (1522 * SCALE, 184 * SCALE)), fill="#111111")
    bar = 500 / (east - west) * WIDTH
    bar_x, bar_y = 88, 900
    ink.rectangle((bar_x * SCALE, bar_y * SCALE, (bar_x + bar) * SCALE, (bar_y + 8) * SCALE), fill="white", outline="#111111", width=2 * SCALE)
    ink.text(((bar_x + bar / 2) * SCALE, (bar_y - 5) * SCALE), "500 m", font=font(15, True), fill="#111111", anchor="mb")
    footer_y = (MAP_HEIGHT + 40) * SCALE
    ink.line(((72 * SCALE, footer_y), (112 * SCALE, footer_y)), fill="#12484a", width=5 * SCALE)
    ink.text((125 * SCALE, footer_y), "Study boundary", font=font(17, True), fill="#111111", anchor="lm")
    ink.line(((490 * SCALE, footer_y), (530 * SCALE, footer_y)), fill="#57706f", width=2 * SCALE)
    ink.text((543 * SCALE, footer_y), "38 intervention zones", font=font(17, True), fill="#111111", anchor="lm")
    ink.rectangle((990 * SCALE, (MAP_HEIGHT + 31) * SCALE, 1010 * SCALE, (MAP_HEIGHT + 49) * SCALE), fill="#d75b33")
    ink.text((1024 * SCALE, footer_y), "21 protected footprints", font=font(17, True), fill="#111111", anchor="lm")
    image.resize((WIDTH, MAP_HEIGHT + FOOTER), Image.Resampling.LANCZOS).save(OUTPUT, optimize=True)
    print(OUTPUT)


if __name__ == "__main__":
    draw()

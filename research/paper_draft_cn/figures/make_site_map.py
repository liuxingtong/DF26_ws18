"""Draw a satellite-to-analysis locator using the same frozen study geometry."""

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
S = 2
W, H = 1640, 840
PHOTO_BOX = (45, 122, 1015, 713)
DIAGRAM_BOX = (1104, 196, 1588, 713)


def features(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))["features"]


def polygons(geometry):
    value = shape(geometry)
    return [value] if value.geom_type == "Polygon" else list(value.geoms) if value.geom_type == "MultiPolygon" else []


def draw():
    meta = json.loads((GROUND / "ground_scene.json").read_text(encoding="utf-8"))
    origin_x, origin_y = meta["bounds"][:2]
    west, south, east, north = meta["local"]
    image = Image.new("RGB", (W * S, H * S), "white")
    ink = ImageDraw.Draw(image)
    ink.text((W * S / 2, 54 * S), "Dapuqiao Study Area", font=font(30, True), fill="#111111", anchor="mm")

    def project(point, box):
        x, y = TRANSFORMER.transform(*point)
        a, b, c, d = box
        u = (x - origin_x - west) / (east - west)
        v = (north - (y - origin_y)) / (north - south)
        return ((a + (0.075 + 0.85 * u) * (c - a)) * S,
                (b + (0.075 + 0.85 * v) * (d - b)) * S)

    photo = Image.open(GROUND / "ground_scene.jpg").convert("RGB")
    pw, ph = PHOTO_BOX[2] - PHOTO_BOX[0], PHOTO_BOX[3] - PHOTO_BOX[1]
    photo = photo.resize((round(pw * S * 0.85), round(ph * S * 0.85)), Image.Resampling.LANCZOS)
    photo = Image.blend(photo, Image.new("RGB", photo.size, "white"), 0.13)
    image.paste(photo, (round((PHOTO_BOX[0] + pw * 0.075) * S), round((PHOTO_BOX[1] + ph * 0.075) * S)))
    ink = ImageDraw.Draw(image, "RGBA")
    ink.rectangle(tuple(v * S for v in DIAGRAM_BOX), fill=(249, 250, 249, 255), outline=(120, 130, 130, 255), width=S)

    for box, schematic in ((PHOTO_BOX, False), (DIAGRAM_BOX, True)):
        if schematic:
            for feature in features("intervention_zones.geojson"):
                for polygon in polygons(feature["geometry"]):
                    ink.line([project(p, box) for p in polygon.exterior.coords], fill=(85, 94, 95, 220), width=2 * S, joint="curve")
        for feature in features("study_boundary.geojson"):
            for polygon in polygons(feature["geometry"]):
                pts = [project(p, box) for p in polygon.exterior.coords]
                ink.line(pts, fill=(255, 255, 255, 255), width=7 * S, joint="curve")
                ink.line(pts, fill=(189, 40, 43, 255), width=4 * S, joint="curve")
        if schematic:
            for feature in features("heritage_buildings.geojson"):
                for polygon in polygons(feature["geometry"]):
                    ink.polygon([project(p, box) for p in polygon.exterior.coords], fill=(24, 106, 105, 255))

    ink = ImageDraw.Draw(image)
    ink.text((530 * S, 101 * S), "Satellite imagery", font=font(19, True), fill="#111111", anchor="mm")
    ink.text((1346 * S, 166 * S), "Study units and heritage", font=font(19, True), fill="#111111", anchor="mm")
    ink.line((1026 * S, 428 * S, 1082 * S, 428 * S), fill="#111111", width=3 * S)
    ink.polygon(((1086 * S, 428 * S), (1073 * S, 420 * S), (1073 * S, 436 * S)), fill="#111111")
    ink.text((952 * S, 152 * S), "N", font=font(18, True), fill="#111111", anchor="mm")
    ink.line((952 * S, 169 * S, 952 * S, 214 * S), fill="#111111", width=2 * S)
    ink.polygon(((952 * S, 162 * S), (945 * S, 178 * S), (959 * S, 178 * S)), fill="#111111")
    bar = 500 / (east - west) * pw * 0.85
    ink.rectangle((140 * S, 644 * S, (140 + bar) * S, 651 * S), fill="white", outline="#111111", width=S)
    ink.text(((140 + bar / 2) * S, 635 * S), "500 m", font=font(14, True), fill="#111111", anchor="mb")
    ink.text((50 * S, 757 * S), "Shanghai · Huangpu · Dapuqiao", font=font(19, True), fill="#111111")
    ink.line((585 * S, 765 * S, 627 * S, 765 * S), fill="#bd282b", width=4 * S)
    ink.text((640 * S, 765 * S), "Study boundary", font=font(15, True), fill="#111111", anchor="lm")
    ink.line((880 * S, 765 * S, 922 * S, 765 * S), fill="#555e5f", width=2 * S)
    ink.text((935 * S, 765 * S), "38 study units", font=font(15, True), fill="#111111", anchor="lm")
    ink.rectangle((1238 * S, 756 * S, 1257 * S, 775 * S), fill="#186a69")
    ink.text((1271 * S, 765 * S), "21 protected footprints", font=font(15, True), fill="#111111", anchor="lm")
    image.resize((W, H), Image.Resampling.LANCZOS).save(OUTPUT, optimize=True)
    print(OUTPUT)


if __name__ == "__main__":
    draw()

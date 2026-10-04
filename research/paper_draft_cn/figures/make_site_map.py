"""Draw georeferenced Shanghai → Dapuqiao → study-unit panels.

Satellite tiles: EOxCloudless Sentinel-2 cloudless 2016 (CC BY 4.0),
https://cloudless.eox.at by EOX IT Services GmbH; modified Copernicus data.
Tile mosaics are cached beside this script for reproducible offline rendering.
"""

import io
import json
import math
import colorsys
from pathlib import Path
from urllib.request import Request, urlopen

from PIL import Image, ImageDraw
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform

from make_preview_pareto import font


ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "05_Shanghai Power to Form Students/data/dapuqiao"
HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "study_area_satellite.png"
MERCATOR = 20037508.342789244
TO_MERC = Transformer.from_crs(4326, 3857, always_xy=True)
S = 2
WIDTH, HEIGHT = 1920, 780
PANELS = ((38, 140, 520, 650), (592, 140, 1268, 650), (1340, 140, 1882, 650))
INK = "#111111"
RED = "#bf3437"

def unit_color(index):
    """Give every study unit a distinct, legible, muted fill."""
    hue = (0.11 + index * 0.61803398875) % 1
    lightness = (0.70, 0.62, 0.76, 0.66)[index % 4]
    saturation = (0.47, 0.53, 0.42)[index % 3]
    rgb = colorsys.hls_to_rgb(hue, lightness, saturation)
    return "#" + "".join(f"{round(channel * 255):02x}" for channel in rgb)


def features(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))["features"]


def area_geometry():
    return transform(TO_MERC.transform, shape(features("study_boundary.geojson")[0]["geometry"]))


def expand_to_aspect(bounds, ratio, margin=0.0):
    x0, y0, x1, y1 = bounds
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    w, h = (x1 - x0) * (1 + margin), (y1 - y0) * (1 + margin)
    if w / h < ratio:
        w = h * ratio
    else:
        h = w / ratio
    return cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2


def tile_pixel(x, y, zoom):
    world = 256 * 2**zoom
    return (x + MERCATOR) / (2 * MERCATOR) * world, (MERCATOR - y) / (2 * MERCATOR) * world


def fetch_raster(extent, zoom, cache):
    if cache.exists():
        return Image.open(cache).convert("RGB")
    x0, y0, x1, y1 = extent
    left, top = tile_pixel(x0, y1, zoom)
    right, bottom = tile_pixel(x1, y0, zoom)
    col0, col1 = math.floor(left / 256), math.floor((right - 1) / 256)
    row0, row1 = math.floor(top / 256), math.floor((bottom - 1) / 256)
    mosaic = Image.new("RGB", ((col1 - col0 + 1) * 256, (row1 - row0 + 1) * 256), "white")
    for row in range(row0, row1 + 1):
        for col in range(col0, col1 + 1):
            url = f"https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless_3857/default/g/{zoom}/{row}/{col}.jpg"
            response = urlopen(Request(url, headers={"User-Agent": "DF26 research figure"}), timeout=25)
            tile = Image.open(io.BytesIO(response.read())).convert("RGB")
            mosaic.paste(tile, ((col - col0) * 256, (row - row0) * 256))
    crop = mosaic.crop((round(left - col0 * 256), round(top - row0 * 256), round(right - col0 * 256), round(bottom - row0 * 256)))
    crop.save(cache, quality=92, optimize=True)
    return crop


def point_in_panel(x, y, extent, panel):
    x0, y0, x1, y1 = extent
    a, b, c, d = panel
    return ((a + (x - x0) / (x1 - x0) * (c - a)) * S,
            (b + (y1 - y) / (y1 - y0) * (d - b)) * S)


def polygon_parts(geometry):
    return [geometry] if geometry.geom_type == "Polygon" else list(geometry.geoms)


def draw_polygon(drawer, polygon, extent, panel, fill=None, outline=None, width=1):
    for part in polygon_parts(polygon):
        points = [point_in_panel(x, y, extent, panel) for x, y in part.exterior.coords]
        if fill:
            drawer.polygon(points, fill=fill)
        if outline:
            drawer.line(points, fill=outline, width=width * S, joint="curve")


def draw():
    area = area_geometry()
    city_box, local_box, units_box = PANELS
    city_bbox = tuple(TO_MERC.transform(x, y) for x, y in ((120.75, 30.55), (122.35, 31.95)))
    city_extent = expand_to_aspect((city_bbox[0][0], city_bbox[0][1], city_bbox[1][0], city_bbox[1][1]),
                                   (city_box[2] - city_box[0]) / (city_box[3] - city_box[1]))
    local_extent = expand_to_aspect(area.bounds,
                                    (local_box[2] - local_box[0]) / (local_box[3] - local_box[1]), margin=0.45)
    image = Image.new("RGB", (WIDTH * S, HEIGHT * S), "white")
    ink = ImageDraw.Draw(image)
    ink.text((WIDTH * S / 2, 56 * S), "Dapuqiao Study Area", font=font(30, True), fill=INK, anchor="mm")
    for panel, title in zip(PANELS, ("Shanghai", "Dapuqiao", "38 study units")):
        ink.text(((panel[0] + panel[2]) * S / 2, 113 * S), title, font=font(20, True), fill=INK, anchor="mm")

    for panel, extent, zoom, cache in ((city_box, city_extent, 9, HERE / "shanghai_sentinel_2016.jpg"),
                                      (local_box, local_extent, 14, HERE / "dapuqiao_sentinel_2016.jpg")):
        raster = fetch_raster(extent, zoom, cache)
        raster = raster.resize(((panel[2] - panel[0]) * S, (panel[3] - panel[1]) * S), Image.Resampling.LANCZOS)
        image.paste(raster, (panel[0] * S, panel[1] * S))

    ink = ImageDraw.Draw(image)
    for panel in PANELS:
        ink.rectangle(tuple(v * S for v in panel), outline="#737c7b", width=S)
    cx, cy = area.centroid.x, area.centroid.y
    px, py = point_in_panel(cx, cy, city_extent, city_box)
    ink.ellipse((px - 10 * S, py - 10 * S, px + 10 * S, py + 10 * S), fill="white", outline=RED, width=4 * S)
    ink.text((px + 16 * S, py - 10 * S), "Dapuqiao", font=font(17, True), fill="white", stroke_width=2 * S, stroke_fill=INK)
    draw_polygon(ink, area, local_extent, local_box, outline="white", width=7)
    draw_polygon(ink, area, local_extent, local_box, outline=RED, width=4)

    for index, feature in enumerate(features("intervention_zones.geojson")):
        geom = transform(TO_MERC.transform, shape(feature["geometry"]))
        draw_polygon(ink, geom, local_extent, units_box, fill=unit_color(index), outline="white", width=2)
    for feature in features("heritage_buildings.geojson"):
        geom = transform(TO_MERC.transform, shape(feature["geometry"]))
        draw_polygon(ink, geom, local_extent, units_box, fill="#1c6968")
    draw_polygon(ink, area, local_extent, units_box, outline=RED, width=4)

    for a, b in ((545, 572), (1293, 1320)):
        ink.line((a * S, 395 * S, b * S, 395 * S), fill=INK, width=3 * S)
        ink.polygon(((b + 8) * S, 395 * S, (b - 5) * S, 387 * S, (b - 5) * S, 403 * S), fill=INK)
    ink.text((1853 * S, 172 * S), "N", font=font(17, True), fill=INK, anchor="mm")
    ink.line((1853 * S, 188 * S, 1853 * S, 225 * S), fill=INK, width=2 * S)
    ink.polygon(((1853 * S, 181 * S), (1846 * S, 196 * S), (1860 * S, 196 * S)), fill=INK)
    local_width_m = local_extent[2] - local_extent[0]
    bar_px = (500 / local_width_m) * (local_box[2] - local_box[0])
    ink.rectangle((620 * S, 612 * S, (620 + bar_px) * S, 620 * S), fill="white", outline=INK, width=S)
    ink.text(((620 + bar_px / 2) * S, 600 * S), "500 m", font=font(14, True), fill="white", stroke_width=S, stroke_fill=INK, anchor="mb")

    ink.line((50 * S, 696 * S, 94 * S, 696 * S), fill=RED, width=4 * S)
    ink.text((106 * S, 696 * S), "Study boundary", font=font(17, True), fill=INK, anchor="lm")
    for i in range(6):
        x = 540 + i * 23
        ink.rectangle((x * S, 687 * S, (x + 18) * S, 705 * S), fill=unit_color(i), outline="#777f7e", width=S)
    ink.text((690 * S, 696 * S), "38 study units · one color each", font=font(17, True), fill=INK, anchor="lm")
    ink.rectangle((1083 * S, 687 * S, 1103 * S, 707 * S), fill="#1c6968")
    ink.text((1116 * S, 696 * S), "Protected footprints", font=font(17, True), fill=INK, anchor="lm")
    ink.text((54 * S, 744 * S), "EOXCloudless 2016 · modified Copernicus Sentinel data · CC BY 4.0", font=font(12), fill="#4a5352")
    image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS).save(OUTPUT, optimize=True)
    print(OUTPUT)


if __name__ == "__main__":
    draw()

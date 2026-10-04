"""Draw georeferenced Shanghai → Dapuqiao → building-function panels."""

import io
import json
import math
from pathlib import Path
from urllib.request import Request, urlopen

import geopandas as gpd
import numpy as np
from PIL import Image, ImageDraw
from pyproj import Transformer
from scipy.ndimage import map_coordinates
from shapely.geometry import shape
from shapely.ops import transform

from make_preview_pareto import font


ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "05_Shanghai Power to Form Students/data/dapuqiao"
HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "study_area_satellite.png"
GROUND = ROOT / "06_AI Render Students/out/dapuqiao"
MERCATOR = 20037508.342789244
TO_MERC = Transformer.from_crs(4326, 3857, always_xy=True)
MERC_TO_UTM = Transformer.from_crs(3857, 32651, always_xy=True)
S = 2
WIDTH, HEIGHT = 1920, 780
PANELS = ((38, 140, 520, 650), (592, 140, 1268, 650), (1340, 140, 1882, 650))
INK = "#111111"
RED = "#bf3437"
FUNCTION_COLORS = {
    "Residential": "#f4e34b",
    "Office": "#d4b65a",
    "Business": "#d659ae",
    "Education": "#e59448",
    "Healthcare": "#527ed2",
    "Culture / sport": "#a38fcd",
    "Park / green": "#469c5b",
    "Other / unknown": "#d9d9d9",
}


def building_function(record):
    """Use recorded EULUC first, with function/AOI only for missing labels."""
    use = str(record.get("euluc") or "")
    function = str(record.get("function") or "")
    aoi = str(record.get("aoi_type2") or "")
    if "公园" in use:
        return "Park / green"
    if "医疗" in use:
        return "Healthcare"
    if "教育" in use:
        return "Education"
    if "体育" in use:
        return "Culture / sport"
    if "商业" in use:
        return "Business"
    if "办公" in use:
        return "Office"
    if "居住" in use:
        return "Residential"
    if "医院" in aoi:
        return "Healthcare"
    if "学校" in aoi:
        return "Education"
    if function == "Business" or "宾馆" in aoi:
        return "Business"
    if function == "Office":
        return "Office"
    if function == "Residence":
        return "Residential"
    return "Other / unknown"


def features(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))["features"]


def area_geometry():
    return transform(TO_MERC.transform, shape(features("study_boundary.geojson")[0]["geometry"]))


def city_geometry():
    cached = HERE / "shanghai_boundary_geoboundaries.geojson"
    return transform(TO_MERC.transform, shape(json.loads(cached.read_text())["features"][0]["geometry"]))


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


def fetch_raster(extent, zoom, cache, provider):
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
            if provider == "osm":
                url = f"https://tile.openstreetmap.org/{zoom}/{col}/{row}.png"
            else:
                url = f"https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless_3857/default/g/{zoom}/{row}/{col}.jpg"
            response = urlopen(Request(url, headers={"User-Agent": "DF26 academic figure (github.com/liuxingtong/DF26_ws18)"}), timeout=25)
            tile = Image.open(io.BytesIO(response.read())).convert("RGB")
            mosaic.paste(tile, ((col - col0) * 256, (row - row0) * 256))
    crop = mosaic.crop((round(left - col0 * 256), round(top - row0 * 256), round(right - col0 * 256), round(bottom - row0 * 256)))
    crop.save(cache, quality=92, optimize=True)
    return crop


def detailed_local_image(extent, panel):
    """Blend the georeferenced Esri cache with Sentinel imagery at its edges."""
    fallback = fetch_raster(extent, 14, HERE / "dapuqiao_sentinel_local_2016.jpg", "eox")
    width, height = (panel[2] - panel[0]) * S, (panel[3] - panel[1]) * S
    base = np.asarray(fallback.resize((width, height), Image.Resampling.LANCZOS), dtype=np.float32)
    meta = json.loads((GROUND / "ground_scene.json").read_text())
    source = np.asarray(Image.open(GROUND / "ground_scene.jpg").convert("RGB"), dtype=np.float32)
    ux0, uy0 = meta["bounds"][0] + meta["local"][0], meta["bounds"][1] + meta["local"][1]
    ux1, uy1 = meta["bounds"][0] + meta["local"][2], meta["bounds"][1] + meta["local"][3]
    xs = np.linspace(extent[0], extent[2], width, endpoint=False) + (extent[2] - extent[0]) / (2 * width)
    ys = np.linspace(extent[3], extent[1], height, endpoint=False) - (extent[3] - extent[1]) / (2 * height)
    mx, my = np.meshgrid(xs, ys)
    ux, uy = MERC_TO_UTM.transform(mx, my)
    col = (ux - ux0) / (ux1 - ux0) * source.shape[1] - 0.5
    row = (uy1 - uy) / (uy1 - uy0) * source.shape[0] - 0.5
    edge = np.minimum.reduce((col, row, source.shape[1] - 1 - col, source.shape[0] - 1 - row))
    alpha = np.clip(edge / 36, 0, 1)[..., None]
    detailed = np.stack([map_coordinates(source[:, :, k], [row, col], order=1, mode="nearest") for k in range(3)], axis=-1)
    return Image.fromarray(np.uint8(np.clip(base * (1 - alpha) + detailed * alpha, 0, 255)))


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
    city = city_geometry()
    city_box, local_box, units_box = PANELS
    city_extent = expand_to_aspect(city.bounds,
                                   (city_box[2] - city_box[0]) / (city_box[3] - city_box[1]), margin=0.07)
    local_extent = expand_to_aspect(area.bounds,
                                    (local_box[2] - local_box[0]) / (local_box[3] - local_box[1]), margin=0.18)
    units_extent = expand_to_aspect(area.bounds,
                                    (units_box[2] - units_box[0]) / (units_box[3] - units_box[1]), margin=0.12)
    image = Image.new("RGB", (WIDTH * S, HEIGHT * S), "white")
    ink = ImageDraw.Draw(image)
    ink.text((WIDTH * S / 2, 56 * S), "Dapuqiao Study Area", font=font(30, True), fill=INK, anchor="mm")
    for panel, title in zip(PANELS, ("Shanghai", "Dapuqiao", "Building functions")):
        ink.text(((panel[0] + panel[2]) * S / 2, 113 * S), title, font=font(20, True), fill=INK, anchor="mm")

    city_raster = fetch_raster(city_extent, 9, HERE / "shanghai_osm_land.jpg", "osm")
    city_raster = city_raster.resize(((city_box[2] - city_box[0]) * S, (city_box[3] - city_box[1]) * S), Image.Resampling.LANCZOS)
    image.paste(city_raster, (city_box[0] * S, city_box[1] * S))
    image.paste(detailed_local_image(local_extent, local_box), (local_box[0] * S, local_box[1] * S))

    ink = ImageDraw.Draw(image, "RGBA")
    for panel in PANELS:
        ink.rectangle(tuple(v * S for v in panel), outline="#737c7b", width=S)
    draw_polygon(ink, city, city_extent, city_box,
                 fill=(248, 230, 119, 95), outline=(58, 64, 55, 235), width=2)
    cx, cy = area.centroid.x, area.centroid.y
    px, py = point_in_panel(cx, cy, city_extent, city_box)
    ink.ellipse((px - 8 * S, py - 8 * S, px + 8 * S, py + 8 * S), fill="white", outline=RED, width=4 * S)
    ink.text((px + 14 * S, py - 9 * S), "Dapuqiao", font=font(17, True), fill="white", stroke_width=2 * S, stroke_fill=INK)
    draw_polygon(ink, area, local_extent, local_box, outline="white", width=7)
    draw_polygon(ink, area, local_extent, local_box, outline=RED, width=4)

    buildings = gpd.read_parquet(DATA / "buildings.parquet").to_crs(3857)
    for _, record in buildings.iterrows():
        draw_polygon(ink, record.geometry, units_extent, units_box,
                     fill=FUNCTION_COLORS[building_function(record)], outline="#373737", width=1)
    draw_polygon(ink, area, units_extent, units_box, outline=RED, width=4)

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

    for index, (label, color) in enumerate(FUNCTION_COLORS.items()):
        col, row = index % 4, index // 4
        x, y = 55 + col * 435, 681 + row * 32
        ink.rectangle((x * S, y * S, (x + 24) * S, (y + 20) * S), fill=color, outline="#444444", width=S)
        ink.text(((x + 34) * S, (y + 10) * S), label, font=font(16, True), fill=INK, anchor="lm")
    ink.line((50 * S, 754 * S, 83 * S, 754 * S), fill=RED, width=3 * S)
    ink.text((95 * S, 754 * S), "Study boundary", font=font(13, True), fill=INK, anchor="lm")
    ink.text((550 * S, 754 * S), "© OpenStreetMap contributors · geoBoundaries 2019 · Esri World Imagery · EOXCloudless 2016 (CC BY 4.0)", font=font(11), fill="#4a5352", anchor="lm")
    image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS).save(OUTPUT, optimize=True)
    print(OUTPUT)


if __name__ == "__main__":
    draw()

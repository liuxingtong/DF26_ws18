"""Draw the paper's single-seed preview figure from the tracked 3D canvas."""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[3]
CANVAS = ROOT / "06_AI Render Students/out/dapuqiao/canvas.html"
OUTPUT = Path(__file__).with_name("preview_pareto_seed11.png")
SCENARIOS = [
    ("public_coordination", "Public coordination"),
    ("development_growth", "Development growth"),
    ("resident_heritage_priority", "Residents and heritage"),
]
SCALE = 2
W, H = 1680, 600


def font(size, bold=False):
    candidates = [
        Path("/Library/Fonts/Microsoft/微软雅黑 Bold.ttf" if bold else "/Library/Fonts/Microsoft/微软雅黑.ttf"),
        Path("/Library/Fonts/Microsoft/msyhbd.ttc" if bold else "/Library/Fonts/Microsoft/msyh.ttc"),
        Path("/System/Library/Fonts/PingFang.ttc"),
    ]
    path = next((item for item in candidates if item.exists()), None)
    if path is None:
        raise FileNotFoundError("Install Microsoft YaHei or a CJK fallback font to render the figure")
    index = 8 if bold and path.name == "PingFang.ttc" else 2 if path.name == "PingFang.ttc" else 0
    return ImageFont.truetype(str(path), size * SCALE, index=index)


def draw():
    source = CANVAS.read_text(encoding="utf-8").split("const GEOM=", 1)[1]
    geom, _ = json.JSONDecoder().raw_decode(source)
    runs = geom["research"]["scenario_runs"]
    image = Image.new("RGB", (W * SCALE, H * SCALE), "#ffffff")
    ink = ImageDraw.Draw(image)

    def line(points, fill, width=1):
        ink.line([(int(x * SCALE), int(y * SCALE)) for x, y in points], fill=fill, width=width * SCALE)

    def text(x, y, value, size=16, fill="#26302e", bold=False, anchor=None):
        ink.text((x * SCALE, y * SCALE), value, font=font(size, bold), fill=fill, anchor=anchor)

    text(W / 2, 52, "Pareto Solutions", 27, "#111111", bold=True, anchor="ma")
    left, top, chart_w, chart_h, gap = 120, 155, 420, 310, 110
    for index, (key, title) in enumerate(SCENARIOS):
        x0 = left + index * (chart_w + gap)
        run = runs[key]
        rows = run["pareto"]
        text(x0 + chart_w / 2, 116, title, 19, "#111111", bold=True, anchor="ma")
        y_label = "Ground release (%)"
        label_font = font(15, True)
        label_w = round(220 * SCALE)
        label = Image.new("RGBA", (label_w, 40 * SCALE), (255, 255, 255, 0))
        ImageDraw.Draw(label).text((label_w / 2, 20 * SCALE), y_label, font=label_font, fill="#111111", anchor="mm")
        label = label.rotate(90, expand=True)
        image.paste(label, (round((x0 - 83) * SCALE), round((top + chart_h / 2) * SCALE - label.height / 2)), label)
        for tick in (0, 0.01, 0.02, 0.03):
            x = x0 + tick / 0.03 * chart_w
            line([(x, top), (x, top + chart_h)], "#e6ebe9")
            text(x, top + chart_h + 10, f"{tick * 100:.0f}%", 13, "#596663", anchor="ma")
        for tick in (0, 0.0002, 0.0004):
            y = top + chart_h - tick / 0.0005 * chart_h
            line([(x0, y), (x0 + chart_w, y)], "#e6ebe9")
            text(x0 - 9, y, f"{tick * 100:.2f}%", 12, "#596663", anchor="rm")
        line([(x0, top), (x0, top + chart_h), (x0 + chart_w, top + chart_h)], "#879592", 2)
        selected = run["selected"]
        for row in rows:
            x = x0 + float(row["development_capacity"]) / 0.03 * chart_w
            y = top + chart_h - float(row["street_connected_released_ground"]) / 0.0005 * chart_h
            exposure = float(row["residential_disruption"])
            t = min(1, exposure / 0.13)
            color = (round(52 + 152 * t), round(134 - 57 * t), round(111 - 47 * t))
            r = 8 * SCALE
            center = (round(x * SCALE), round(y * SCALE))
            ink.ellipse((center[0] - r, center[1] - r, center[0] + r, center[1] + r), fill=color, outline="white", width=2 * SCALE)
            if row["solution_id"] in (selected.get("resident"), selected.get("development"), selected.get("public_planning")):
                rr = 12 * SCALE
                ink.ellipse((center[0] - rr, center[1] - rr, center[0] + rr, center[1] + rr), outline="#26302e", width=2 * SCALE)
        text(x0 + chart_w / 2, 513, "Added GFA (%)", 15, "#111111", bold=True, anchor="ma")
    text(120, 563, "Residential exposure", 14, "#111111", bold=True)
    for i, color in enumerate(("#34866f", "#77796c", "#cc4d40")):
        x = 312 + i * 65
        ink.ellipse((x * SCALE, 567 * SCALE, (x + 14) * SCALE, 581 * SCALE), fill=color)
    text(515, 563, "low to high", 13, "#111111")
    text(1100, 563, "Outline: role selection", 13, "#111111")
    image.resize((W, H), Image.Resampling.LANCZOS).save(OUTPUT, optimize=True)
    print(OUTPUT)


if __name__ == "__main__":
    draw()

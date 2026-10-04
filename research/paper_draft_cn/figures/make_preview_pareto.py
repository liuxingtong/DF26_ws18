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
    family = "Arial Bold.ttf" if bold else "Arial.ttf"
    path = Path("/System/Library/Fonts/Supplemental") / family
    return ImageFont.truetype(str(path), size * SCALE)


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

    text(70, 35, "Pareto solutions by governance scenario", 25, bold=True)
    text(70, 76, "Preview only · seed 11 · 60 independent evaluations per scenario", 15, "#596663")
    text(70, 104, "Y axis: street-facing ground release / site area", 13, "#596663")
    left, top, chart_w, chart_h, gap = 95, 162, 425, 300, 82
    for index, (key, title) in enumerate(SCENARIOS):
        x0 = left + index * (chart_w + gap)
        run = runs[key]
        rows = run["pareto"]
        text(x0, 126, title, 18, bold=True)
        text(x0 + chart_w, 126, f"n = {len(rows)}", 14, "#596663", anchor="ra")
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
        text(x0 + chart_w / 2, 520, "Positive GFA additions / site area", 14, "#465450", anchor="ma")
    text(95, 567, "Color: residential exposure", 14, "#596663")
    for i, color in enumerate(("#34866f", "#77796c", "#cc4d40")):
        x = 302 + i * 94
        ink.ellipse((x * SCALE, 567 * SCALE, (x + 14) * SCALE, 581 * SCALE), fill=color)
    text(605, 567, "low                 high", 13, "#596663")
    text(1160, 567, "Outlined: selected by at least one role", 13, "#596663")
    image.resize((W, H), Image.Resampling.LANCZOS).save(OUTPUT, optimize=True)
    print(OUTPUT)


if __name__ == "__main__":
    draw()

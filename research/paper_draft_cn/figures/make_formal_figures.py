"""Draw paper figures from the completed four-method formal experiment."""

import csv
import math
from pathlib import Path

from PIL import Image, ImageDraw

from make_preview_pareto import font


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "research/paper_draft_cn/data/formal_three_scenario_20261004"
HERE = Path(__file__).resolve().parent
S = 2
INK = "#111111"
GRID = "#dbe3e0"
COLORS = ("#555f63", "#16716b", "#c45d42", "#8a6b3f")
METHODS = (
    ("conventional_parameter_baseline", "Parameter baseline"),
    ("public_coordination", "Public coordination"),
    ("development_growth", "Development growth"),
    ("resident_heritage_priority", "Residents and heritage"),
)


def rows(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def setup(width, height, title):
    image = Image.new("RGB", (width * S, height * S), "white")
    draw = ImageDraw.Draw(image)
    label(draw, width / 2, 49, title, 29, bold=True, anchor="mm")
    return image, draw


def label(draw, x, y, value, size=16, bold=False, anchor=None, fill=INK):
    draw.text((round(x * S), round(y * S)), value, font=font(size, bold), fill=fill, anchor=anchor)


def vertical(image, x, y, value, size=16):
    temp = Image.new("RGBA", (310 * S, 38 * S), (255, 255, 255, 0))
    ImageDraw.Draw(temp).text((155 * S, 19 * S), value, font=font(size, True), fill=INK, anchor="mm")
    temp = temp.rotate(90, expand=True)
    image.paste(temp, (round(x * S - temp.width / 2), round(y * S - temp.height / 2)), temp)


def line(draw, x1, y1, x2, y2, fill=GRID, width=1):
    draw.line((round(x1 * S), round(y1 * S), round(x2 * S), round(y2 * S)), fill=fill, width=width * S)


def save(image, name, width, height):
    path = HERE / name
    image.resize((width, height), Image.Resampling.LANCZOS).save(path, optimize=True)
    print(path)


def scale_max(values, floor=0.001):
    top = max(max(values, default=0), floor) * 1.1
    magnitude = 10 ** math.floor(math.log10(top))
    return math.ceil(top / magnitude * 2) / 2 * magnitude


def front_figure():
    width, height = 1760, 630
    image, draw = setup(width, height, "Pareto Solutions Across Five Seeds")
    fronts = {}
    for key, _ in METHODS:
        fronts[key] = []
        for seed in (11, 23, 37, 53, 71):
            path = SOURCE / "runs" / key / f"seed_{seed}" / "pareto_solutions.csv"
            fronts[key].extend(rows(path))
    xmax = scale_max([float(row["development_capacity"]) for items in fronts.values() for row in items])
    ymax = scale_max([float(row["street_connected_released_ground"]) for items in fronts.values() for row in items], 0.0001)
    left, top, pw, ph, gap = 126, 167, 340, 320, 78
    for index, (key, heading) in enumerate(METHODS):
        x0 = left + index * (pw + gap)
        label(draw, x0 + pw / 2, 122, heading, 17, bold=True, anchor="mm")
        vertical(image, x0 - 75, top + ph / 2, "Ground release (%)", 14)
        for step in range(5):
            x = x0 + step * pw / 4
            y = top + step * ph / 4
            line(draw, x, top, x, top + ph)
            line(draw, x0, y, x0 + pw, y)
            label(draw, x, top + ph + 12, f"{step * xmax * 25:.1f}", 12, anchor="ma", fill=INK)
            label(draw, x0 - 11, top + ph - step * ph / 4, f"{step * ymax * 25:.2f}", 12, anchor="rm", fill=INK)
        line(draw, x0, top, x0, top + ph, "#697976", 2)
        line(draw, x0, top + ph, x0 + pw, top + ph, "#697976", 2)
        for row in fronts[key]:
            x = x0 + min(1, float(row["development_capacity"]) / xmax) * pw
            y = top + ph - min(1, float(row["street_connected_released_ground"]) / ymax) * ph
            exposure = min(1, float(row["residential_disruption"]) / 0.35)
            color = (round(35 + 170 * exposure), round(130 - 67 * exposure), round(112 - 57 * exposure))
            r = 4 * S
            draw.ellipse((round(x * S) - r, round(y * S) - r, round(x * S) + r, round(y * S) + r), fill=color, outline="white", width=S)
        label(draw, x0 + pw / 2, 548, "Added GFA (%)", 15, bold=True, anchor="mm")
    label(draw, 110, 597, "Residential exposure", 14, bold=True)
    for index, color in enumerate(("#238270", "#7d7754", "#cd3f37")):
        x = 322 + index * 63
        draw.ellipse((x * S, 597 * S, (x + 15) * S, 612 * S), fill=color)
    label(draw, 523, 596, "low to high", 13)
    save(image, "formal_pareto_fronts.png", width, height)


def quality_figure():
    width, height = 1460, 590
    image, draw = setup(width, height, "Search Quality")
    indexed = {row["method_id"]: row for row in rows(SOURCE / "aggregate_summary.csv")}
    panels = (("hypervolume", "Hypervolume", "Hypervolume"), ("spacing", "Spacing", "Spacing"))
    for panel, (metric, heading, yname) in enumerate(panels):
        x0, top, pw, ph = 105 + panel * 730, 153, 565, 315
        label(draw, x0 + pw / 2, 116, heading, 19, bold=True, anchor="mm")
        vertical(image, x0 - 65, top + ph / 2, yname, 15)
        values = [float(indexed[key][f"{metric}_mean"]) for key, _ in METHODS]
        errors = [float(indexed[key][f"{metric}_std"]) for key, _ in METHODS]
        maximum = scale_max([value + error for value, error in zip(values, errors)])
        for step in range(5):
            y = top + ph - step * ph / 4
            line(draw, x0, y, x0 + pw, y)
            label(draw, x0 - 9, y, f"{step * maximum / 4:.3f}", 12, anchor="rm")
        line(draw, x0, top, x0, top + ph, "#697976", 2)
        for idx, (_, name) in enumerate(METHODS):
            cx = x0 + 76 + idx * 137
            value, error = values[idx], errors[idx]
            bar_top = top + ph - value / maximum * ph
            draw.rectangle((round((cx - 27) * S), round(bar_top * S), round((cx + 27) * S), round((top + ph) * S)), fill=COLORS[idx])
            err_y1 = top + ph - (value + error) / maximum * ph
            err_y2 = top + ph - max(0, value - error) / maximum * ph
            line(draw, cx, err_y1, cx, err_y2, INK, 2)
            line(draw, cx - 9, err_y1, cx + 9, err_y1, INK, 2)
            line(draw, cx - 9, err_y2, cx + 9, err_y2, INK, 2)
            words = ("Baseline", "Public", "Growth", "Resident")
            label(draw, cx, 487, words[idx], 13, bold=True, anchor="ma")
    save(image, "formal_quality_metrics.png", width, height)


def coverage_figure():
    width, height = 1450, 590
    image, draw = setup(width, height, "Dominance Coverage")
    grouped = {}
    for row in rows(SOURCE / "baseline_scenario_coverage.csv"):
        grouped.setdefault(row["scenario_id"], []).append(row)
    left, top, pw, ph, gap = 110, 150, 345, 315, 123
    for index, (key, heading) in enumerate(METHODS[1:]):
        x0 = left + index * (pw + gap)
        label(draw, x0 + pw / 2, 113, heading, 17, bold=True, anchor="mm")
        vertical(image, x0 - 62, top + ph / 2, "Dominated share", 15)
        for step in range(5):
            y = top + ph - step * ph / 4
            line(draw, x0, y, x0 + pw, y)
            label(draw, x0 - 9, y, f"{step * 25}%", 12, anchor="rm")
        line(draw, x0, top, x0, top + ph, "#697976", 2)
        values = (
            sum(float(row["scenario_over_baseline"]) for row in grouped[key]) / 5,
            sum(float(row["baseline_over_scenario"]) for row in grouped[key]) / 5,
        )
        for j, (value, name, color) in enumerate(zip(values, ("Scenario", "Baseline"), ("#16716b", "#c45d42"))):
            cx = x0 + 100 + j * 145
            y = top + ph - value * ph
            draw.rectangle((round((cx - 36) * S), round(y * S), round((cx + 36) * S), round((top + ph) * S)), fill=color)
            label(draw, cx, max(top + 15, y - 12), f"{value * 100:.1f}%", 14, bold=True, anchor="mm")
            label(draw, cx, 489, name, 14, bold=True, anchor="ma")
    save(image, "formal_dominance_coverage.png", width, height)


if __name__ == "__main__":
    if not (SOURCE / "fairness_audit.csv").exists():
        raise SystemExit("Formal experiment has not completed")
    front_figure()
    quality_figure()
    coverage_figure()

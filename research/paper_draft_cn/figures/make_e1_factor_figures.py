#!/usr/bin/env python3
"""E1 因子消融图：容量探针 vs 改动范围，以及前沿极值 vs 改动范围。

左图：确定性探针的容量上限（3 情景 × 3 范围档 × 2 attribution）。
右图：320 次 NSGA-II 的前沿最大净增建（attribution off，3 seed 散点 + 均值）。
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[3] / "05_Shanghai Power to Form Students" / "out" / "dapuqiao" / "results_v2"
SCOPE_DIR = ROOT / "e1_scope_3seeds_b320"
OUTPUT = Path(__file__).resolve().parent / "e1_dimension_vs_scope.png"

SCENARIOS = (
    ("public_coordination", "PC", "#1f77b4"),
    ("development_growth", "DG", "#d62728"),
    ("resident_heritage_priority", "RH", "#2ca02c"),
)
SCOPES = ("tight", "mid", "loose")
SCOPE_LABELS = {"tight": "tight\n0.22 / 0.14", "mid": "mid\n0.30 / 0.18", "loose": "loose\n0.45 / 0.30"}


def load_probe() -> dict[tuple[str, str, str], float]:
    data = {}
    for path in sorted((SCOPE_DIR / "probes").glob("*/*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        data[(payload["scenario"], payload["scope"], payload["attribution"])] = payload["capacity"]
    return data


def load_runs() -> dict[tuple[str, str], list[float]]:
    data: dict[tuple[str, str], list[float]] = {}
    for path in sorted((SCOPE_DIR / "runs").glob("*/*/seed_*/summary.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        data.setdefault((payload["scenario"], payload["scope"]), []).append(payload["max_net"])
    return data


def main() -> int:
    probes = load_probe()
    runs = load_runs()
    figure, (left, right) = plt.subplots(1, 2, figsize=(11, 4.2))

    x = range(len(SCOPES))
    for scenario, label, colour in SCENARIOS:
        for attribution, style in (("off", "-o"), ("on", "--s")):
            values = [100 * probes.get((scenario, scope, attribution), float("nan")) for scope in SCOPES]
            left.plot(x, values, style, color=colour, alpha=1.0 if attribution == "off" else 0.45,
                      label=f"{label} · labels {attribution}")
    left.set_xticks(list(x))
    left.set_xticklabels([SCOPE_LABELS[scope] for scope in SCOPES], fontsize=8)
    left.set_ylabel("capacity bound, % net GFA")
    left.set_title("Deterministic capacity probe (800 evaluations)")
    left.grid(alpha=0.25)
    left.legend(fontsize=7, ncol=2, frameon=False)

    for index, (scenario, label, colour) in enumerate(SCENARIOS):
        offset = (index - 1) * 0.09
        for position, scope in enumerate(SCOPES):
            values = [100 * value for value in runs.get((scenario, scope), [])]
            if not values:
                continue
            right.scatter([position + offset] * len(values), values, s=14,
                          color=colour, alpha=0.55, zorder=3)
            right.hlines(sum(values) / len(values), position + offset - 0.05, position + offset + 0.05,
                         color=colour, linewidth=2.0, zorder=4)
        right.plot([], [], color=colour, label=label)
    right.set_xticks(list(x))
    right.set_xticklabels([SCOPE_LABELS[scope] for scope in SCOPES], fontsize=8)
    right.set_ylabel("front max net GFA, %")
    right.set_title("NSGA-II front extreme, labels off (3 seeds)")
    right.grid(alpha=0.25)
    right.legend(fontsize=8, frameon=False)

    figure.tight_layout()
    figure.savefig(OUTPUT, dpi=200)
    print(f"wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

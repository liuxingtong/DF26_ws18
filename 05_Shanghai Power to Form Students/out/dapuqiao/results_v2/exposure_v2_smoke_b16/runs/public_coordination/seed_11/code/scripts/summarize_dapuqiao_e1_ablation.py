#!/usr/bin/env python3
"""汇总 E1 2x2x2 因子消融：主效应、交互项与逐 seed 明细。

读取 ``run_dapuqiao_e1_ablation.py`` 的输出目录，按 2x2x2 平衡设计对每个情景估计
三个主效应与四个交互项（符号编码，效应 = 高水位均值 − 低水位均值）。

    ../.venv/bin/python scripts/summarize_dapuqiao_e1_ablation.py \
        --input out/dapuqiao/results_v2/e1_factorial_3seeds_b320
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path


FACTORS = ("attribution", "operator_set", "intensity")
EXPECTED_ARMS = {
    f"attr-{a}__ops-{o}__int-{i}"
    for a in ("on", "off")
    for o in ("own", "union")
    for i in ("own", "common")
}
LEVELS = {"on": 1, "off": -1, "own": -1, "union": 1, "common": 1}

# 匹配预算下 BL 的容量参照（e0_stage3seeds_b320_fixed，3 seed 均值）。
BL_320_CAPACITY = 0.05948476973018587


def parse_arm(arm_id: str) -> dict[str, int]:
    codes: dict[str, int] = {}
    for token in arm_id.split("__"):
        name, value = token.split("-", 1)
        key = {"attr": "attribution", "ops": "operator_set", "int": "intensity"}[name]
        codes[key] = LEVELS[value]
    missing = set(FACTORS) - set(codes)
    if missing:
        raise ValueError(f"臂名缺少因子：{missing}（{arm_id}）")
    return codes


def effect(values: list[float], codes: list[dict[str, int]], terms: tuple[str, ...]) -> float:
    """平衡 ±1 编码下的效应：高水位均值 − 低水位均值。

    mean(code * value) = (mean_high - mean_low) / 2，因此乘 2 还原为水位差。
    """
    signed = []
    for value, code in zip(values, codes):
        sign = 1
        for term in terms:
            sign *= code[term]
        signed.append(sign * value)
    return 2.0 * statistics.mean(signed)


def interaction_name(terms: tuple[str, ...]) -> str:
    return " x ".join(terms)


def load_summary(path: Path) -> list[dict]:
    """优先读 CSV；运行未结束时回退到逐 run 的 summary.json。"""
    if path.is_file():
        with path.open(newline="", encoding="utf-8-sig") as handle:
            return list(csv.DictReader(handle))
    rows = []
    for item in sorted(path.glob("runs/*/*/seed_*/summary.json")):
        rows.append(json.loads(item.read_text(encoding="utf-8")))
    return rows


def load_probe_summary(path: Path) -> list[dict]:
    if path.is_file():
        with path.open(newline="", encoding="utf-8-sig") as handle:
            return list(csv.DictReader(handle))
    rows = []
    for item in sorted(path.glob("probes/*/*.json")):
        rows.append(json.loads(item.read_text(encoding="utf-8")))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    rows = load_summary(
        args.input / "summary.csv" if (args.input / "summary.csv").exists() else args.input
    )
    output = args.output or args.input
    by_scenario: dict[str, list[dict]] = {}
    for row in rows:
        by_scenario.setdefault(row["scenario"], []).append(row)

    effects_rows = []
    balanced: dict[str, bool] = {}
    for scenario, items in by_scenario.items():
        arms = {item["arm"] for item in items}
        counts = {sum(1 for entry in items if entry["arm"] == arm) for arm in arms}
        balanced[scenario] = arms == EXPECTED_ARMS and len(counts) == 1

    for scenario, items in sorted(by_scenario.items()):
        if not balanced[scenario]:
            continue
        codes = [parse_arm(item["arm"]) for item in items]
        for metric in ("max_net_front", "max_release_front", "hypervolume", "pareto", "effective"):
            values = [float(item[metric]) for item in items]
            for terms in (
                ("attribution",), ("operator_set",), ("intensity",),
                ("attribution", "operator_set"),
                ("attribution", "intensity"),
                ("operator_set", "intensity"),
                ("attribution", "operator_set", "intensity"),
            ):
                effects_rows.append({
                    "scenario": scenario,
                    "metric": metric,
                    "term": interaction_name(terms),
                    "effect": effect(values, codes, terms),
                })

    with (output / "factorial_effects.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=["scenario", "metric", "term", "effect"])
        writer.writeheader()
        writer.writerows(effects_rows)

    lines: list[str] = ["# E1 2x2x2 因子消融汇总", ""]
    lines.append(
        "效应 = 高水位均值 − 低水位均值。attribution：on(保留标签) − off(移除标签)；"
        "operator_set：union(六算子) − own(情景原值)；intensity：common(统一上限) − own(原值)。"
    )
    lines.append("")
    for scenario, items in sorted(by_scenario.items()):
        lines.append(f"## {scenario}")
        lines.append("")
        lines.append("| 臂 | n | 前沿最大净增建 | 有效候选最大净增建 | 最大临街释放 | Pareto | HV |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|")
        grouped: dict[str, list[float]] = {}
        for item in items:
            grouped.setdefault(item["arm"], []).append(item)
        for arm, arm_items in sorted(grouped.items()):
            def mean(metric: str) -> float:
                return statistics.mean(float(entry[metric]) for entry in arm_items)
            lines.append(
                f"| `{arm}` | {len(arm_items)} | {100 * mean('max_net_front'):.3f}% | "
                f"{100 * mean('max_net_effective'):.3f}% | "
                f"{100 * mean('max_release_front'):.3f}% | {mean('pareto'):.1f} | "
                f"{mean('hypervolume'):.3f} |"
            )
        lines.append("")
        if not balanced[scenario]:
            lines.append("> 该情景的臂不全或各臂 seed 数不等，已跳过效应估计（设计不是平衡的）。")
            lines.append("")
            continue
        scenario_effects = [row for row in effects_rows if row["scenario"] == scenario]
        for metric, scale, suffix in (
            ("max_net_front", 100, "%"), ("max_release_front", 100, "%"), ("hypervolume", 1, ""),
        ):
            lines.append(f"**{metric} 效应**（{suffix or '原值'}）")
            lines.append("")
            for row in scenario_effects:
                if row["metric"] == metric:
                    lines.append(f"- {row['term']}：{scale * row['effect']:+.3f}{suffix}")
            lines.append("")
        reference = statistics.mean(
            float(entry["max_net_front"]) for entry in grouped["attr-on__ops-own__int-own"]
        ) if "attr-on__ops-own__int-own" in grouped else None
        if reference is not None:
            lines.append(
                f"参照：该批 R 臂最大净增建均值 {100 * reference:.3f}%，"
                f"匹配预算 BL 容量参照 {100 * BL_320_CAPACITY:.3f}%。"
            )
            lines.append("")

    probe_path = args.input / "probe_summary.csv"
    probe_rows = load_probe_summary(probe_path if probe_path.exists() else args.input)
    if probe_rows:
        by_scenario_probe: dict[str, list[dict]] = {}
        for row in probe_rows:
            by_scenario_probe.setdefault(row["scenario"], []).append(row)
        lines.append("## 容量探针（确定性贪心，320 次原始评价）")
        lines.append("")
        for scenario, items in sorted(by_scenario_probe.items()):
            if {item["arm"] for item in items} != EXPECTED_ARMS:
                continue
            codes = [parse_arm(item["arm"]) for item in items]
            values = [float(item["capacity"]) for item in items]
            lines.append(f"**{scenario}**")
            lines.append("")
            lines.append("| 臂 | 容量上限 | 相对 BL | 改动单元 |")
            lines.append("|---|---:|---:|---:|")
            for item in sorted(items, key=lambda entry: -float(entry["capacity"])):
                capacity = float(item["capacity"])
                lines.append(
                    f"| `{item['arm']}` | {100 * capacity:.3f}% | "
                    f"{100 * capacity / BL_320_CAPACITY:.1f}% | {item['changed_zones']} |"
                )
            lines.append("")
            for terms in (("attribution",), ("operator_set",), ("intensity",)):
                value = effect(values, codes, terms)
                lines.append(f"- {interaction_name(terms)} 效应：{100 * value:+.3f}%")
            lines.append("")

    (output / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    (output / "report.json").write_text(
        json.dumps(
            {"effects": effects_rows, "source": str(args.input)},
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

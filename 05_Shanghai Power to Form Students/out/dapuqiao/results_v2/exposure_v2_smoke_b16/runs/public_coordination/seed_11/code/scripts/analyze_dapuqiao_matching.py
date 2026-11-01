#!/usr/bin/env python3
"""E6 匹配比较：匹配净增建 与 匹配居住扰动。

读取 ``runs/<method>/seed_<seed>/all_candidates.csv``（E0 正式运行或 320 次套件均可），
在给定的净增建 / 居住扰动分档内筛选可行候选，回答两个问题：

- 相同净增建下，哪个方法的居住扰动最低（并记录该候选的临街释放）。
- 相同居住扰动下，哪个方法的净增建与临街释放最高。

约定：

- 只报真正匹配上的候选；某方法在某档没有候选时写 ``unreachable``，**不插值、不借用相邻档**。
- 同时输出每档的匹配候选数，匹配数很小时结论只能当描述性证据。
- 跨 seed 汇总给均值 / 标准差 / 有匹配的 seed 数。

    ../.venv/bin/python scripts/analyze_dapuqiao_matching.py \
        --runs out/dapuqiao/results_v2/e0_stage3seeds_b320_fixed/runs \
        --methods public_coordination,development_growth,resident_heritage_priority \
        --output out/dapuqiao/results_v2/e0_stage3seeds_b320_fixed/matching
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path


METHODS = {
    "conventional_parameter_baseline": "BL",
    "public_coordination": "PC",
    "development_growth": "DG",
    "resident_heritage_priority": "RH",
}


SHORT = {
    "public_coordination": "PC",
    "development_growth": "DG",
    "resident_heritage_priority": "RH",
    "conventional_parameter_baseline": "BL",
}


def candidate_path(runs: Path, method: str, seed: int, layout: str, arm: str) -> Path:
    if layout == "arm":
        return runs / method / arm / f"seed_{seed}" / "candidates.csv"
    return runs / method / f"seed_{seed}" / "all_candidates.csv"


def load_candidates(runs: Path, method: str, seed: int, layout: str = "method", arm: str = "") -> list[dict]:
    path = candidate_path(runs, method, seed, layout, arm)
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = []
        for row in csv.DictReader(handle):
            if row["feasible"].strip().lower() != "true":
                continue
            rows.append({
                "solution_id": row["solution_id"],
                "disruption": float(row["residential_disruption"]),
                "capacity": float(row["development_capacity"]),
                "release": float(row["street_connected_released_ground"]),
                "changed_zones": int(row["changed_zone_count"]),
                "changed_buildings": float(row["changed_buildings"]),
            })
        return rows


def match_capacity(rows: list[dict], target: float, tolerance: float) -> list[dict]:
    low, high = target - tolerance, target + tolerance
    return [row for row in rows if low <= row["capacity"] <= high]


def match_disruption(rows: list[dict], ceiling: float, tolerance: float = 0.0) -> list[dict]:
    """居住扰动不超过上限的候选（含边界）。"""
    limit = ceiling + max(tolerance, 0.0)
    return [row for row in rows if row["disruption"] <= limit + 1e-12]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path, required=True)
    parser.add_argument("--methods", default="public_coordination,development_growth,resident_heritage_priority")
    parser.add_argument("--seeds", default="11,23,37")
    parser.add_argument("--capacity-bands", default="0.0,0.2,0.4,0.6",
                        help="净增建分档（%），逗号分隔")
    parser.add_argument("--capacity-tolerance", type=float, default=0.05,
                        help="净增建容差（百分点）")
    parser.add_argument("--disruption-ceilings", default="0,5,10,20,30",
                        help="居住扰动上限（%），逗号分隔：统计不超过该值的候选")
    parser.add_argument("--layout", choices=("method", "arm"), default="method",
                        help="method：runs/<method>/seed_X/all_candidates.csv；"
                             "arm：runs/<scenario>/<arm>/seed_X/candidates.csv")
    parser.add_argument("--arm", default="attr-on__ops-own__int-own",
                        help="layout=arm 时的臂名")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    methods = [value.strip() for value in args.methods.split(",") if value.strip()]
    seeds = [int(value.strip()) for value in args.seeds.split(",") if value.strip()]
    capacity_bands = [float(v) for v in args.capacity_bands.split(",") if v.strip()]
    disruption_ceilings = [float(v) for v in args.disruption_ceilings.split(",") if v.strip()]
    output = args.output or (args.runs.parent / "matching")
    output.mkdir(parents=True, exist_ok=True)

    capacity_rows: list[dict] = []
    disruption_rows: list[dict] = []
    for method in methods:
        for seed in seeds:
            rows = load_candidates(args.runs, method, seed, args.layout, args.arm)
            for band in capacity_bands:
                matched = match_capacity(rows, band / 100.0, args.capacity_tolerance / 100.0)
                best = min(matched, key=lambda row: row["disruption"]) if matched else None
                capacity_rows.append({
                    "method": METHODS.get(method, method),
                    "method_id": method,
                    "seed": seed,
                    "capacity_band_pct": band,
                    "matched_count": len(matched),
                    "min_disruption_pct": None if best is None else 100 * best["disruption"],
                    "mean_disruption_pct": (
                        None if not matched
                        else 100 * statistics.mean(row["disruption"] for row in matched)
                    ),
                    "capacity_mean_pct": (
                        None if not matched
                        else 100 * statistics.mean(row["capacity"] for row in matched)
                    ),
                    "capacity_at_min_pct": None if best is None else 100 * best["capacity"],
                    "release_at_min_pct": None if best is None else 100 * best["release"],
                    "changed_zones_at_min": None if best is None else best["changed_zones"],
                    "solution_id": None if best is None else best["solution_id"],
                })
            for ceiling in disruption_ceilings:
                matched = match_disruption(rows, ceiling / 100.0)
                best = max(matched, key=lambda row: row["capacity"]) if matched else None
                disruption_rows.append({
                    "method": METHODS.get(method, method),
                    "method_id": method,
                    "seed": seed,
                    "disruption_ceiling_pct": ceiling,
                    "matched_count": len(matched),
                    "max_capacity_pct": None if best is None else 100 * best["capacity"],
                    "max_release_pct": None if not matched else 100 * max(
                        row["release"] for row in matched
                    ),
                    "solution_id": None if best is None else best["solution_id"],
                    "changed_zones_at_max": None if best is None else best["changed_zones"],
                })

    with (output / "matched_capacity_detail.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(capacity_rows[0]))
        writer.writeheader()
        writer.writerows(capacity_rows)
    with (output / "matched_disruption_detail.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(disruption_rows[0]))
        writer.writeheader()
        writer.writerows(disruption_rows)

    # 跨 seed 汇总：均值 / 标准差 / 覆盖率
    def summarise(rows: list[dict], band_key: str, value_key: str) -> list[dict]:
        grouped: dict[tuple[float, str], list[dict]] = {}
        for row in rows:
            grouped.setdefault((row[band_key], row["method"]), []).append(row)
        out = []
        for (band, method), items in sorted(grouped.items()):
            values = [item[value_key] for item in items if item[value_key] is not None]
            out.append({
                band_key: band,
                "method": method,
                "seeds_total": len(items),
                "seeds_matched": len(values),
                "mean": statistics.mean(values) if values else None,
                "std": statistics.stdev(values) if len(values) > 1 else (0.0 if values else None),
                "min": min(values) if values else None,
                "max": max(values) if values else None,
            })
        return out

    capacity_summary = summarise(capacity_rows, "capacity_band_pct", "min_disruption_pct")
    capacity_summary_mean = summarise(capacity_rows, "capacity_band_pct", "mean_disruption_pct")
    disruption_summary = summarise(disruption_rows, "disruption_ceiling_pct", "max_capacity_pct")
    with (output / "matched_capacity_summary.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(capacity_summary[0]))
        writer.writeheader()
        writer.writerows(capacity_summary)
    with (output / "matched_disruption_summary.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(disruption_summary[0]))
        writer.writeheader()
        writer.writerows(disruption_summary)

    lines = ["# E6 匹配比较", ""]
    lines.append(
        f"净增建匹配用 ±{args.capacity_tolerance}pp 容差；居住扰动一侧用上限筛选（≤ 该值），"
        "因为「相同代价下能拿多少收益」比窄带匹配更贴近公平比较的问法。"
        "没有候选的格子写 unreachable，不插值。"
    )
    lines.append("")
    lines.append("## 相同净增建下的居住扰动（%）：最小值 / 匹配候选均值")
    lines.append("")
    lines.append("| 净增建档 | " + " | ".join(METHODS.get(m, m) for m in methods) + " |")
    lines.append("|---|" + "---|" * len(methods))
    for band in capacity_bands:
        cells = []
        for method in methods:
            item = next(
                (row for row in capacity_summary
                 if row["capacity_band_pct"] == band and row["method"] == METHODS.get(method, method)),
                None,
            )
            mean_item = next(
                (row for row in capacity_summary_mean
                 if row["capacity_band_pct"] == band and row["method"] == METHODS.get(method, method)),
                None,
            )
            if item is None or item["mean"] is None:
                cells.append("unreachable")
            else:
                cells.append(
                    f"{item['mean']:.2f} / {mean_item['mean']:.2f}（n={item['seeds_matched']}）"
                )
        lines.append(f"| {band:.1f}% | " + " | ".join(cells) + " |")
    lines.append("")
    lines.append("## 居住扰动不超过给定值时的最大净增建（%）")
    lines.append("")
    lines.append("| 扰动上限 | " + " | ".join(METHODS.get(m, m) for m in methods) + " |")
    lines.append("|---|" + "---|" * len(methods))
    for band in disruption_ceilings:
        cells = []
        for method in methods:
            item = next(
                (row for row in disruption_summary
                 if row["disruption_ceiling_pct"] == band and row["method"] == METHODS.get(method, method)),
                None,
            )
            if item is None or item["mean"] is None:
                cells.append("unreachable")
            else:
                cells.append(f"{item['mean']:.2f}（n={item['seeds_matched']}）")
        lines.append(f"| {band:.0f}% | " + " | ".join(cells) + " |")
    lines.append("")
    lines.append("## 匹配候选数（诊断用）")
    lines.append("")
    for band in capacity_bands:
        counts = {
            row["method"]: row["matched_count"]
            for row in capacity_rows if row["capacity_band_pct"] == band
        }
        lines.append(
            f"- 净增建 {band:.1f}%：" + "，".join(f"{k} {v}" for k, v in sorted(counts.items()))
        )
    lines.append("")

    (output / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (output / "summary.json").write_text(
        json.dumps({
            "runs": str(args.runs),
            "methods": methods,
            "seeds": seeds,
            "capacity": {"bands_pct": capacity_bands, "tolerance_pp": args.capacity_tolerance},
            "disruption": {"ceiling_pct": disruption_ceilings},
            "note": "unreachable 表示该方法在该档没有可行候选；不做插值。",
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("\n".join(lines))
    print(f"输出：{output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

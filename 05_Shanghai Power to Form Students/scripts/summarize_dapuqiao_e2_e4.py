#!/usr/bin/env python3
"""E2 行为分布表 + E4 角色优先级稳定性汇总。

三块内容：

- E2-A：各方法的算子出现率（读 E0 正式的 ``operation_activity.csv``，10 seed）。
- E2-B：被改建筑的主体构成（读候选表，逐候选统计 resident/developer/state/unknown）。
- E4：相邻优先级交换后，首选方案是否改变，以及首选层的并列规模。

    ../.venv/bin/python scripts/summarize_dapuqiao_e2_e4.py \
        --runs out/dapuqiao/results_v2/e0_stage3seeds_b320_fixed/runs \
        --operation-activity out/dapuqiao/results_v2/e0_formal_remote_20261029/operation_activity.csv \
        --output out/dapuqiao/results_v2/e0_stage3seeds_b320_fixed/e2_e4
"""

from __future__ import annotations

import argparse
import csv
import statistics
from collections import Counter, defaultdict
from pathlib import Path


METHOD = {
    "conventional_parameter_baseline": "BL",
    "public_coordination": "PC",
    "development_growth": "DG",
    "resident_heritage_priority": "RH",
}
ROLE = {"resident": "居民", "development": "开发", "public_planning": "公共规划"}


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv_report(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def operator_table(activity: Path) -> list[dict]:
    rows = read_csv(activity)
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        grouped[(row["method"], row["operator"])].append(row)
    output = []
    for (method, operator), items in sorted(grouped.items()):
        output.append({
            "method": method,
            "operator": operator,
            "seed_count": len(items),
            "candidate_prevalence_mean": statistics.mean(
                float(item["candidate_prevalence"]) for item in items
            ),
            "operator_decision_count_mean": statistics.mean(
                float(item["operator_decision_count"]) for item in items
            ),
        })
    return output


def stakeholder_table(runs: Path) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for path in sorted(runs.glob("*/seed_*/all_candidates.csv")):
        method = METHOD.get(path.parts[-3], path.parts[-3])
        for row in read_csv(path):
            if row["feasible"].strip().lower() != "true":
                continue
            if int(float(row["changed_zone_count"])) == 0:
                continue
            grouped[method].append(row)
    output = []
    for method, items in sorted(grouped.items()):
        def mean(key: str) -> float:
            return statistics.mean(float(item[key]) for item in items)
        changed = mean("changed_buildings")
        resident = mean("changed_resident_buildings")
        developer = mean("changed_developer_buildings")
        state = mean("changed_state_buildings")
        unknown = mean("changed_unknown_buildings")
        known = resident + developer + state
        output.append({
            "method": method,
            "candidates": len(items),
            "changed_buildings_mean": changed,
            "changed_zones_mean": mean("changed_zone_count"),
            "resident_share": resident / known if known else 0.0,
            "developer_share": developer / known if known else 0.0,
            "state_share": state / known if known else 0.0,
            "unknown_buildings_mean": unknown,
            "densify_mean": mean("densify_count"),
            "open_ground_mean": mean("open_ground_count"),
            "split_mean": mean("split_to_towers_count"),
            "step_down_mean": mean("heritage_step_down_count"),
            "public_space_mean": mean("public_space_reconfiguration_count"),
            "courtyard_mean": mean("courtyard_access_improvement_count"),
        })
    return output


def role_table(runs: Path) -> list[dict]:
    counts: Counter = Counter()
    changed: Counter = Counter()
    ties: dict[tuple[str, str], list[int]] = defaultdict(list)
    for path in sorted(runs.glob("*/seed_*/role_priority_sensitivity.csv")):
        method = METHOD.get(path.parts[-3], path.parts[-3])
        rows = read_csv(path)
        base = {row["role"]: row for row in rows if row["variant_type"] == "base"}
        for role, row in base.items():
            ties[(method, role)].append(int(row["accepted_count"]))
        for row in rows:
            if row["variant_type"] == "base":
                continue
            key = (method, row["role"], row["parameter"])
            counts[key] += 1
            if row["selected_solution_id"] != base[row["role"]]["selected_solution_id"]:
                changed[key] += 1
    output = []
    for key in sorted(counts):
        method, role, parameter = key
        output.append({
            "method": method,
            "role": ROLE.get(role, role),
            "swap": parameter,
            "cases": counts[key],
            "changed": changed[key],
            "changed_rate": changed[key] / counts[key],
            "base_tie_size_mean": statistics.mean(ties[(method, role)]),
        })
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path, required=True)
    parser.add_argument("--operation-activity", type=Path, default=None)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    operators = operator_table(args.operation_activity) if args.operation_activity else []
    stakeholders = stakeholder_table(args.runs)
    roles = role_table(args.runs)

    write_csv_report(args.output / "e2_operator_prevalence.csv", operators)
    write_csv_report(args.output / "e2_stakeholder_mix.csv", stakeholders)
    write_csv_report(args.output / "e4_role_stability.csv", roles)

    lines = ["# E2 行为分布与 E4 角色优先级稳定性", ""]
    if operators:
        lines += ["## E2-A 算子出现率（正式 E0，10 seed）", "",
                  "| 方法 | 算子 | 出现率均值 | 每候选决策数 |", "|---|---|---:|---:|"]
        for row in operators:
            if row["method"] == "BL":
                continue
            lines.append(
                f"| {row['method']} | `{row['operator']}` | "
                f"{100 * row['candidate_prevalence_mean']:.1f}% | "
                f"{row['operator_decision_count_mean']:.0f} |"
            )
        lines.append("")
    lines += ["## E2-B 被改建筑的主体构成（候选级，3 seed）", "",
              "| 方法 | 改建筑/候选 | 改单元/候选 | 居民占比 | 开发占比 | 公共占比 |",
              "|---|---:|---:|---:|---:|---:|"]
    for row in stakeholders:
        lines.append(
            f"| {row['method']} | {row['changed_buildings_mean']:.1f} | "
            f"{row['changed_zones_mean']:.1f} | {100 * row['resident_share']:.1f}% | "
            f"{100 * row['developer_share']:.1f}% | {100 * row['state_share']:.1f}% |"
        )
    lines.append("")
    lines += ["## E4 相邻优先级交换后的首选方案变化", "",
              "| 方法 | 角色 | 交换 | 变化次数/总次数 | 变化率 | 首选层并列数 |",
              "|---|---|---|---:|---:|---:|"]
    for row in roles:
        lines.append(
            f"| {row['method']} | {row['role']} | {row['swap']} | "
            f"{row['changed']}/{row['cases']} | {100 * row['changed_rate']:.0f}% | "
            f"{row['base_tie_size_mean']:.1f} |"
        )
    lines.append("")
    if roles:
        overall = sum(row["changed"] for row in roles) / sum(row["cases"] for row in roles)
        lines.append(f"合计变化率：{100 * overall:.0f}%。")
        lines.append("")

    (args.output / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"输出：{args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

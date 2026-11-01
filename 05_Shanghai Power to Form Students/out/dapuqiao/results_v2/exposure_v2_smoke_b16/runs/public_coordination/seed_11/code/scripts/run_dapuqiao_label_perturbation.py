#!/usr/bin/env python3
"""标签误分类敏感性：随机翻转 resident/developer 标签后重测容量探针。

只测 attribution on（真实权限表）下的容量，因为归属解除后容量由全部可编辑存量决定，
标签噪声的影响会被稀释。翻转只在 resident 与 developer 之间进行：state 的不可编辑
是结构性排除，翻转它会改变实验设定本身，不属于"标签误差"。

    ../.venv/bin/python scripts/run_dapuqiao_label_perturbation.py \
        --jobs 6 --output out/dapuqiao/results_v2/label_perturbation_probe
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

WS05 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WS05))
sys.path.insert(0, str(WS05 / "scripts"))

from run_dapuqiao_e1_ablation import (  # noqa: E402
    ARMS,
    config_hashes,
    run_capacity_probe,
    transform_scenario,
)
from engine.optimization.amplitude import apply_operator_arm, arm_metadata, resolve_arm  # noqa: E402
from engine.optimization.data import CONFIG_ROOT, load_study, load_yaml  # noqa: E402


SCENARIOS = ("public_coordination", "development_growth")
LEVELS = (0.0, 0.05, 0.10)
REPS = 3


def build_study(spec: dict[str, Any]):
    study = load_study(spec["scenario"], research_demo=False, shared_experiment_controls=True)
    if study.blockers:
        raise RuntimeError(f"{spec['scenario']} 输入仍有阻塞项：{study.blockers}")
    study.scenario = transform_scenario(
        study.scenario, ARMS["attr-on__ops-own__int-own"]
    )["scenario"]
    level = spec["level"]
    if level > 0:
        buildings = study.buildings.copy()
        rng = np.random.default_rng(10_000 * spec["rep"] + int(round(level * 1000)))
        candidates = buildings.index[
            buildings["stakeholder_proxy"].isin(["resident", "developer"])
        ]
        count = int(round(len(candidates) * level))
        flipped = rng.choice(candidates, size=count, replace=False)
        swapped = buildings.loc[flipped, "stakeholder_proxy"].map(
            {"resident": "developer", "developer": "resident"}
        )
        buildings.loc[flipped, "stakeholder_proxy"] = swapped
        buildings["residential_proxy"] = buildings["stakeholder_proxy"].eq("resident")
        buildings["editable"] = ~buildings["stakeholder_proxy"].eq("state")
        study.buildings = buildings
    study.retain_candidate_geometries = False
    share = float(study.buildings["stakeholder_proxy"].eq("developer").mean())
    return study, share


def run_task(spec: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    study, developer_share = build_study(spec)
    payload = run_capacity_probe(study, spec["operator_specs"], budget=spec["budget"])
    payload.update({
        "scenario": spec["scenario"],
        "level": spec["level"],
        "rep": spec["rep"],
        "developer_share": developer_share,
        "runtime_seconds": time.perf_counter() - started,
    })
    return payload


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenarios", default=",".join(SCENARIOS))
    parser.add_argument("--levels", default=",".join(str(v) for v in LEVELS))
    parser.add_argument("--reps", type=int, default=REPS)
    parser.add_argument("--probe-budget", type=int, default=320)
    parser.add_argument("--amplitude-arm", default=None)
    parser.add_argument("--jobs", type=int, default=6)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    scenarios = [v.strip() for v in args.scenarios.split(",") if v.strip()]
    levels = [float(v) for v in args.levels.split(",") if v.strip()]
    output = args.output
    if output.exists() and any(output.iterdir()) and not args.overwrite:
        raise SystemExit(f"输出目录非空：{output}")
    output.mkdir(parents=True, exist_ok=True)

    arm_id, arm = resolve_arm(args.amplitude_arm)
    operator_specs = apply_operator_arm(
        load_yaml(CONFIG_ROOT / "operator_specs.yaml").get("operators", {}), arm
    )

    tasks = [
        {"scenario": scenario, "level": level, "rep": rep,
         "budget": args.probe_budget, "operator_specs": operator_specs}
        for scenario in scenarios
        for level in levels
        for rep in (range(args.reps) if level > 0 else [0])
    ]

    started = time.perf_counter()
    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        futures = {pool.submit(run_task, spec): spec for spec in tasks}
        for future in as_completed(futures):
            spec = futures[future]
            try:
                payload = future.result()
            except Exception as error:  # noqa: BLE001
                failures.append({**spec, "operator_specs": None, "error": repr(error)})
                continue
            results.append(payload)
            print(
                f"[{len(results)}/{len(tasks)}] {payload['scenario']} "
                f"noise={100 * payload['level']:.0f}% rep={payload['rep']} "
                f"cap={100 * payload['capacity']:.3f}% "
                f"dev_share={100 * payload['developer_share']:.1f}% "
                f"zones={payload['changed_zones']}",
                flush=True,
            )

    results.sort(key=lambda item: (item["scenario"], item["level"], item["rep"]))
    write_csv(output / "probe_summary.csv", results)

    summary = []
    for scenario in scenarios:
        for level in levels:
            items = [r for r in results if r["scenario"] == scenario and r["level"] == level]
            if not items:
                continue
            summary.append({
                "scenario": scenario,
                "noise_level": level,
                "reps": len(items),
                "capacity_mean_pct": 100 * statistics.mean(r["capacity"] for r in items),
                "capacity_min_pct": 100 * min(r["capacity"] for r in items),
                "capacity_max_pct": 100 * max(r["capacity"] for r in items),
                "disruption_mean_pct": 100 * statistics.mean(r["disruption"] for r in items),
                "developer_share_mean": statistics.mean(r["developer_share"] for r in items),
                "changed_zones_mean": statistics.mean(r["changed_zones"] for r in items),
            })
    write_csv(output / "label_summary.csv", summary)

    lines = ["# 标签误分类敏感性（探针，attribution on，320 次预算）", ""]
    lines.append("| 情景 | 噪声 | 容量均值 | 范围 | 开发主体占比 | 改动单元 |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for row in summary:
        lines.append(
            f"| {row['scenario']} | {100 * row['noise_level']:.0f}% | "
            f"{row['capacity_mean_pct']:.3f}% | "
            f"{row['capacity_min_pct']:.3f}–{row['capacity_max_pct']:.3f}% | "
            f"{100 * row['developer_share_mean']:.1f}% | {row['changed_zones_mean']:.1f} |"
        )
    lines.append("")
    (output / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (output / "manifest.json").write_text(
        json.dumps({
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "script": str(Path(__file__).relative_to(WS05)),
            "layer": "E2-label-perturbation",
            "scenarios": scenarios,
            "levels": levels,
            "reps": args.reps,
            "flip_rule": "只在 resident 与 developer 之间翻转；state 不参与",
            "attribution": "on",
            "probe_raw_calls": args.probe_budget,
            "amplitude_arm": arm_metadata(arm_id, arm),
            "config_sha256": config_hashes(),
            "probe_count": len(results),
            "failure_count": len(failures),
            "elapsed_seconds": time.perf_counter() - started,
        }, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    print("\n".join(lines))
    print(f"完成：{output}（{len(results)} probes, {len(failures)} failures）")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())

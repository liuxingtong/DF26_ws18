#!/usr/bin/env python3
"""E5 包络敏感性：共同限高 / FAR / 覆盖率的一次一因子探针。

共同包络在 ``load_study(shared_experiment_controls=True)`` 时会写进逐单元控制表，
所以这里同时改 ``scenario["defaults"]`` 与 ``study.controls`` 的同名列，二者必须一致。

只跑 attribution off（容量被打开的区间），且只跑 PC/DG：RH 的操作集合里没有增容算子，
任何包络变化都不会产生净增建（见 §11），把它当对照记 0 即可。

    ../.venv/bin/python scripts/run_dapuqiao_e5_envelope.py \
        --jobs 6 --probe-budget 800 \
        --output out/dapuqiao/results_v2/e5_envelope_probe
"""

from __future__ import annotations

import argparse
import csv
import json
import platform
import statistics
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from importlib import metadata as package_metadata
from pathlib import Path
from typing import Any

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
FACTORS: dict[str, tuple[str, list[float]]] = {
    "height_limit_m": ("限高 m", [24.0, 30.0, 36.0, 45.0]),
    "max_far": ("FAR", [2.5, 3.0, 3.5]),
    "max_coverage_ratio": ("覆盖率", [0.50, 0.60, 0.70]),
}
BASELINE = {"height_limit_m": 36.0, "max_far": 3.0, "max_coverage_ratio": 0.60}


def build_study(spec: dict[str, Any]):
    study = load_study(
        spec["scenario"],
        research_demo=False,
        shared_experiment_controls=True,
    )
    if study.blockers:
        raise RuntimeError(f"{spec['scenario']} 输入仍有阻塞项：{study.blockers}")
    transformed = transform_scenario(study.scenario, ARMS["attr-off__ops-own__int-own"])
    study.scenario = transformed["scenario"]
    key, value = spec["factor"], spec["value"]
    study.scenario["defaults"][key] = value
    if study.controls is not None:
        study.controls = study.controls.copy()
        study.controls[key] = value
    study.retain_candidate_geometries = False
    return study


def run_task(spec: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    study = build_study(spec)
    payload = run_capacity_probe(study, spec["operator_specs"], budget=spec["budget"])
    payload.update({
        "scenario": spec["scenario"],
        "factor": spec["factor"],
        "value": spec["value"],
        "is_baseline": spec["value"] == BASELINE[spec["factor"]],
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
    parser.add_argument("--factors", default=",".join(FACTORS))
    parser.add_argument("--probe-budget", type=int, default=800)
    parser.add_argument("--amplitude-arm", default=None)
    parser.add_argument("--jobs", type=int, default=6)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    scenarios = [value.strip() for value in args.scenarios.split(",") if value.strip()]
    factors = [value.strip() for value in args.factors.split(",") if value.strip()]
    for name in factors:
        if name not in FACTORS:
            raise KeyError(f"未知因子：{name}")
    output = args.output
    if output.exists() and any(output.iterdir()) and not args.overwrite:
        raise SystemExit(f"输出目录非空：{output}")
    output.mkdir(parents=True, exist_ok=True)

    arm_id, arm = resolve_arm(args.amplitude_arm)
    operator_specs = apply_operator_arm(
        load_yaml(CONFIG_ROOT / "operator_specs.yaml").get("operators", {}), arm
    )

    tasks = [
        {"scenario": scenario, "factor": factor, "value": value,
         "budget": args.probe_budget, "operator_specs": operator_specs}
        for scenario in scenarios
        for factor in factors
        for value in FACTORS[factor][1]
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
                print(f"FAILED {spec['scenario']} {spec['factor']}={spec['value']}: {error}",
                      file=sys.stderr, flush=True)
                continue
            results.append(payload)
            print(
                f"[{len(results)}/{len(tasks)}] {payload['scenario']} "
                f"{payload['factor']}={payload['value']:g} "
                f"cap={100 * payload['capacity']:.3f}% "
                f"disr={100 * payload['disruption']:.1f}% "
                f"zones={payload['changed_zones']} "
                f"calls={payload['calls']} ({payload['runtime_seconds']:.0f}s)",
                flush=True,
            )

    results.sort(key=lambda item: (item["scenario"], item["factor"], item["value"]))
    write_csv(output / "probe_summary.csv", results)

    rows = []
    for scenario in scenarios:
        for factor in factors:
            items = [item for item in results
                     if item["scenario"] == scenario and item["factor"] == factor]
            base = next((item for item in items if item["is_baseline"]), None)
            for item in items:
                rows.append({
                    "scenario": scenario,
                    "factor": factor,
                    "value": item["value"],
                    "capacity_pct": 100 * item["capacity"],
                    "disruption_pct": 100 * item["disruption"],
                    "changed_zones": item["changed_zones"],
                    "calls": item["calls"],
                    "budget_exhausted": item["budget_exhausted"],
                    "delta_vs_baseline_pp": (
                        None if base is None else 100 * (item["capacity"] - base["capacity"])
                    ),
                })
    write_csv(output / "probe_effects.csv", rows)

    lines = ["# E5 包络敏感性（探针，attribution off）", ""]
    for scenario in scenarios:
        lines.append(f"## {scenario}")
        lines.append("")
        lines.append("| 因子 | 取值 | 容量 | 相对基线 | 扰动 | 改动单元 | 预算耗尽 |")
        lines.append("|---|---:|---:|---:|---:|---:|---|")
        for row in rows:
            if row["scenario"] != scenario:
                continue
            delta = "—" if row["delta_vs_baseline_pp"] is None else f"{row['delta_vs_baseline_pp']:+.3f}pp"
            lines.append(
                f"| {row['factor']} | {row['value']:g} | {row['capacity_pct']:.3f}% | {delta} | "
                f"{row['disruption_pct']:.1f}% | {row['changed_zones']} | "
                f"{'是' if row['budget_exhausted'] else '否'} |"
            )
        lines.append("")
    (output / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "script": str(Path(__file__).relative_to(WS05)),
        "layer": "E5-envelope-probe",
        "scenarios": scenarios,
        "factors": {name: list(FACTORS[name][1]) for name in factors},
        "baseline": BASELINE,
        "attribution": "off",
        "probe_raw_calls": args.probe_budget,
        "note": "确定性贪心探针；RH 未纳入，因为其操作集合无增容算子（容量恒为 0）。",
        "amplitude_arm": arm_metadata(arm_id, arm),
        "config_sha256": config_hashes(),
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "pymoo": package_metadata.version("pymoo"),
        },
        "probe_count": len(results),
        "failure_count": len(failures),
        "elapsed_seconds": time.perf_counter() - started,
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8"
    )
    if failures:
        (output / "failures.json").write_text(
            json.dumps(failures, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(f"\n完成：{output}（{len(results)} probes, {len(failures)} failures, "
          f"{manifest['elapsed_seconds'] / 60:.1f} min）")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""E1 第三层：改动范围（implementation scope）消融。

前两层已确认 PC/DG 的容量主要由 attribution 决定。本层把 ``implementation``
里的两个比例当作独立的治理旋钮：

- ``tight``：zone 0.22 / building 0.14（RH 原值）
- ``mid``：zone 0.30 / building 0.18（PC 原值）
- ``loose``：zone 0.45 / building 0.30（DG 原值）

设计取舍：标签保留（attribution on）时，容量只有 0.6% 量级，探针在 6 个单元内即收敛，
远低于三个上限，范围不可能是紧约束；因此 NSGA-II 只跑 attribution off（容量真正被打开
的区间），attribution on 只跑确定性探针作为对照。探针预算提到 800 次，因为上一批在 320 次
时移除标签的探针全部耗尽预算、无法判断范围是否成为紧约束。

用法（在 05_Shanghai Power to Form Students 下）：

    ../.venv/bin/python scripts/run_dapuqiao_e1_scope.py \
        --seeds 11,23,37 --jobs 6 --output out/dapuqiao/results_v2/e1_scope_3seeds_b320
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
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
    decision_rows,
    summarise,
    transform_scenario,
    write_csv,
)
from engine.optimization.amplitude import (  # noqa: E402
    apply_operator_arm,
    arm_metadata,
    resolve_arm,
)
from engine.optimization.data import CONFIG_ROOT, load_study, load_yaml  # noqa: E402
from engine.optimization.nsga2 import run_nsga2  # noqa: E402
from run_dapuqiao_e1_ablation import run_capacity_probe  # noqa: E402


SCENARIOS = (
    "public_coordination",
    "development_growth",
    "resident_heritage_priority",
)
SCOPE_LEVELS: dict[str, tuple[float, float]] = {
    "tight": (0.22, 0.14),
    "mid": (0.30, 0.18),
    "loose": (0.45, 0.30),
}
SCOPE_OWNERS = {"tight": "resident_heritage_priority", "mid": "public_coordination", "loose": "development_growth"}


def apply_scope(scenario: dict[str, Any], level: str) -> dict[str, Any]:
    zone_ratio, building_ratio = SCOPE_LEVELS[level]
    result = deepcopy(scenario)
    implementation = result.setdefault("implementation", {})
    before = dict(implementation)
    implementation["maximum_changed_zone_ratio"] = zone_ratio
    implementation["maximum_changed_building_ratio"] = building_ratio
    return {
        "scenario": result,
        "diff": {"before": before, "after": dict(implementation)},
    }


def build_study(spec: dict[str, Any]):
    study = load_study(
        spec["scenario"],
        research_demo=False,
        shared_experiment_controls=spec["control_envelope"] == "shared",
    )
    if study.blockers:
        raise RuntimeError(f"{spec['scenario']} 输入仍有阻塞项：{study.blockers}")
    arm = ARMS[f"attr-{spec['attribution']}__ops-own__int-own"]
    transformed = transform_scenario(study.scenario, arm)
    scoped = apply_scope(transformed["scenario"], spec["scope"])
    study.scenario = scoped["scenario"]
    study.retain_candidate_geometries = False
    return study, {"arm": transformed["diff"], "scope": scoped["diff"]}


def run_nsga2_task(spec: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    study, diff = build_study(spec)
    candidates, pareto, metadata = run_nsga2(
        study,
        spec["operator_specs"],
        population=spec["population"],
        generations=spec["generations"],
        seed=spec["seed"],
        evaluation_budget=spec["budget"],
        fixed_raw_budget=True,
    )
    payload = {
        "scenario": spec["scenario"],
        "scope": spec["scope"],
        "attribution": spec["attribution"],
        "seed": spec["seed"],
        "budget": spec["budget"],
        "population": spec["population"],
        "generations": spec["generations"],
        "diff": diff,
        "runtime_seconds": time.perf_counter() - started,
        **summarise(candidates, pareto, metadata, study.objective_config),
    }
    return {
        "kind": "nsga2",
        "scenario": spec["scenario"],
        "scope": spec["scope"],
        "attribution": spec["attribution"],
        "seed": spec["seed"],
        "summary": payload,
        "rows": decision_rows(candidates),
        "scenario_after": study.scenario,
    }


def run_probe_task(spec: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    study, diff = build_study(spec)
    payload = run_capacity_probe(study, spec["operator_specs"], budget=spec["budget"])
    payload.update({
        "scenario": spec["scenario"],
        "scope": spec["scope"],
        "attribution": spec["attribution"],
        "diff": diff,
        "runtime_seconds": time.perf_counter() - started,
    })
    return {
        "kind": "probe",
        "scenario": spec["scenario"],
        "scope": spec["scope"],
        "attribution": spec["attribution"],
        "summary": payload,
    }


METRICS = ("max_net", "max_net_effective", "max_release", "hypervolume", "pareto")


def aggregate(rows: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    grouped: dict[tuple, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(tuple(row[key] for key in keys), []).append(row)
    output = []
    for group_key, items in sorted(grouped.items()):
        entry: dict[str, Any] = dict(zip(keys, group_key))
        entry["n"] = len(items)
        for metric in METRICS:
            values = [float(item[metric]) for item in items]
            entry[f"{metric}_mean"] = statistics.mean(values)
            entry[f"{metric}_std"] = statistics.stdev(values) if len(values) > 1 else 0.0
        output.append(entry)
    return output


def probe_aggregate(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((row["scenario"], row["scope"], row["attribution"]), []).append(row)
    output = []
    for group_key, items in sorted(grouped.items()):
        scenario, scope, attribution = group_key
        entry = {
            "scenario": scenario,
            "scope": scope,
            "attribution": attribution,
            "n": len(items),
            "capacity_mean": statistics.mean(float(item["capacity"]) for item in items),
            "capacity_min": min(float(item["capacity"]) for item in items),
            "capacity_max": max(float(item["capacity"]) for item in items),
            "disruption_mean": statistics.mean(float(item["disruption"]) for item in items),
            "changed_zones_mean": statistics.mean(float(item["changed_zones"]) for item in items),
            "budget_exhausted": any(bool(item["budget_exhausted"]) for item in items),
            "calls_mean": statistics.mean(float(item["calls"]) for item in items),
        }
        output.append(entry)
    return output


def scope_effects(probe_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """范围效应用 loose − tight 的线性对比；同时给出 attribution 与交互。"""
    table: dict[tuple[str, str], dict[str, float]] = {}
    for row in probe_rows:
        key = (row["scenario"], row["attribution"])
        table.setdefault(key, {})[row["scope"]] = float(row["capacity"])
    effects = []
    for (scenario, attribution), values in sorted(table.items()):
        if not {"tight", "mid", "loose"} <= set(values):
            continue
        effects.append({
            "scenario": scenario,
            "attribution": attribution,
            "scope_loose_minus_tight": values["loose"] - values["tight"],
            "scope_mid_minus_tight": values["mid"] - values["tight"],
            "capacity_tight": values["tight"],
            "capacity_mid": values["mid"],
            "capacity_loose": values["loose"],
        })
    return effects


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", default="11,23,37")
    parser.add_argument("--scenarios", default=",".join(SCENARIOS))
    parser.add_argument("--scopes", default="tight,mid,loose")
    parser.add_argument("--probe-attribution", default="on,off")
    parser.add_argument("--population", type=int, default=16)
    parser.add_argument("--generations", type=int, default=20)
    parser.add_argument("--budget", type=int, default=320)
    parser.add_argument("--probe-budget", type=int, default=800)
    parser.add_argument("--amplitude-arm", default=None)
    parser.add_argument("--control-envelope", choices=("shared", "frozen_per_zone"), default="shared")
    parser.add_argument("--jobs", type=int, default=6)
    parser.add_argument("--probe-only", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    seeds = [int(value.strip()) for value in args.seeds.split(",") if value.strip()]
    scenarios = [value.strip() for value in args.scenarios.split(",") if value.strip()]
    scopes = [value.strip() for value in args.scopes.split(",") if value.strip()]
    probe_attribution = [v.strip() for v in args.probe_attribution.split(",") if v.strip()]
    for name in scopes:
        if name not in SCOPE_LEVELS:
            raise KeyError(f"未知 scope 档位：{name}")
    output: Path = args.output
    if output.exists() and any(output.iterdir()) and not args.overwrite:
        raise SystemExit(f"输出目录非空：{output}")
    output.mkdir(parents=True, exist_ok=True)

    arm_id, arm = resolve_arm(args.amplitude_arm)
    operator_specs = apply_operator_arm(
        load_yaml(CONFIG_ROOT / "operator_specs.yaml").get("operators", {}), arm
    )

    tasks: list[dict[str, Any]] = []
    if not args.probe_only:
        for scenario in scenarios:
            for scope in scopes:
                for seed in seeds:
                    tasks.append({
                        "kind": "nsga2", "scenario": scenario, "scope": scope,
                        "attribution": "off", "seed": seed,
                        "population": args.population, "generations": args.generations,
                        "budget": args.budget, "operator_specs": operator_specs,
                        "control_envelope": args.control_envelope,
                    })
    for scenario in scenarios:
        for scope in scopes:
            for attribution in probe_attribution:
                tasks.append({
                    "kind": "probe", "scenario": scenario, "scope": scope,
                    "attribution": attribution, "seed": None,
                    "budget": args.probe_budget, "operator_specs": operator_specs,
                    "control_envelope": args.control_envelope,
                })

    started = time.perf_counter()
    summaries: list[dict[str, Any]] = []
    probes: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    def record(result: dict[str, Any]) -> None:
        if result["kind"] == "nsga2":
            run_dir = output / "runs" / result["scenario"] / result["scope"] / f"seed_{result['seed']}"
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "summary.json").write_text(
                json.dumps(result["summary"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            write_csv(run_dir / "candidates.csv", result["rows"])
            summaries.append(result["summary"])
            s = result["summary"]
            print(
                f"[{len(summaries)}/{len(tasks)}] {s['scenario']} scope={s['scope']} "
                f"seed={s['seed']} net={100 * s['max_net']:.3f}% "
                f"zones<=? pareto={s['pareto']} ({s['runtime_seconds']:.0f}s)",
                flush=True,
            )
        else:
            probe_dir = output / "probes" / result["scenario"]
            probe_dir.mkdir(parents=True, exist_ok=True)
            name = f"scope-{result['scope']}__attr-{result['attribution']}.json"
            (probe_dir / name).write_text(
                json.dumps(result["summary"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            probes.append(result["summary"])
            s = result["summary"]
            print(
                f"[probe {len(probes)}] {s['scenario']} scope={s['scope']} attr={s['attribution']} "
                f"cap={100 * s['capacity']:.3f}% zones={s['changed_zones']} "
                f"calls={s['calls']} exhausted={s['budget_exhausted']}",
                flush=True,
            )

    if args.jobs <= 1:
        for spec in tasks:
            try:
                record(run_nsga2_task(spec) if spec["kind"] == "nsga2" else run_probe_task(spec))
            except Exception as error:  # noqa: BLE001
                failures.append({**spec, "operator_specs": None, "error": repr(error)})
                print(f"FAILED {spec}: {error}", file=sys.stderr, flush=True)
    else:
        with ProcessPoolExecutor(max_workers=args.jobs) as pool:
            futures = {
                pool.submit(run_nsga2_task if spec["kind"] == "nsga2" else run_probe_task, spec): spec
                for spec in tasks
            }
            for future in as_completed(futures):
                spec = futures[future]
                try:
                    record(future.result())
                except Exception as error:  # noqa: BLE001
                    failures.append({**spec, "operator_specs": None, "error": repr(error)})
                    print(f"FAILED {spec}: {error}", file=sys.stderr, flush=True)

    write_csv(output / "summary.csv", summaries)
    write_csv(output / "aggregate_summary.csv", aggregate(summaries, ("scenario", "scope", "attribution")))
    write_csv(output / "probe_summary.csv", probes)
    write_csv(output / "probe_aggregate.csv", probe_aggregate(probes))
    write_csv(output / "probe_effects.csv", scope_effects(probes))
    if failures:
        (output / "failures.json").write_text(
            json.dumps(failures, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    manifest = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "script": str(Path(__file__).relative_to(WS05)),
        "study": "dapuqiao",
        "layer": "E1-scope",
        "scenarios": scenarios,
        "seeds": seeds,
        "scopes": {name: list(SCOPE_LEVELS[name]) for name in scopes},
        "scope_owner_scenario": SCOPE_OWNERS,
        "nsga2_attribution": "off",
        "probe_attribution": probe_attribution,
        "rationale": (
            "attribution on 时容量仅 0.6% 量级且探针在 6 个单元内收敛（低于 8/11/17 上限），"
            "范围不可能是紧约束，故 NSGA-II 只跑 attribution off；on 只做探针对照。"
        ),
        "budget": {
            "nsga2_raw_calls": args.budget,
            "population": args.population,
            "generations": args.generations,
            "probe_raw_calls": args.probe_budget,
            "fixed_raw_budget": True,
        },
        "amplitude_arm": arm_metadata(arm_id, arm),
        "control_envelope": args.control_envelope,
        "config_sha256": config_hashes(),
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "pymoo": package_metadata.version("pymoo"),
            "geopandas": package_metadata.version("geopandas"),
        },
        "run_count": len(summaries),
        "probe_count": len(probes),
        "failure_count": len(failures),
        "elapsed_seconds": time.perf_counter() - started,
        "statutory_planning_result": False,
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8"
    )
    print(
        f"\n完成：{output} ({len(summaries)} runs, {len(probes)} probes, {len(failures)} failures, "
        f"{manifest['elapsed_seconds'] / 60:.1f} min)"
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())

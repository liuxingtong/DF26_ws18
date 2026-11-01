#!/usr/bin/env python3
"""E1 权限表分解消融（2x2x2）与等预算容量探针。

三个可独立变化的因子：

- ``attribution``：``stakeholder_targets`` 保留 / 移除（"谁可以操作"）。
- ``operator_set``：``allowed_operators`` 用情景原值 / 取六算子并集（"哪些操作被允许"）。
- ``intensity``：``maximum_intensity`` 用情景原值 / 统一表（"同样一次操作能推到多强"）。

``implementation``（最大改动范围）、共同控制包络、遗产冻结与目标口径在所有臂中保持不变；
它们属于 E1 后续的第三层消融，不在本脚本内。

每次 NSGA-II run 固定 320 次原始评价（population 16 × 20 代、固定预算），与
``e0_stage3seeds_b320_fixed`` 同形同种子，因此 R 臂应当复现该套件的数值，其余臂可直接配对比较。

容量探针（``--probe``）是确定性的贪心饱和搜索，同样消耗 320 次原始评价，只回答
"这张权限表最多能推到多少净增建"，不与 NSGA-II 的前沿质量混用。

用法（在 05_Shanghai Power to Form Students 下）：

    ../.venv/bin/python scripts/run_dapuqiao_e1_ablation.py \
        --seeds 11,23,37 --jobs 6 --probe \
        --output out/dapuqiao/results_v2/e1_factorial_3seeds_b320
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import statistics
import sys
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
from datetime import datetime
from importlib import metadata as package_metadata
from pathlib import Path
from typing import Any

WS05 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WS05))

from engine.optimization.amplitude import (  # noqa: E402
    apply_operator_arm,
    arm_metadata,
    resolve_arm,
)
from engine.optimization.data import CONFIG_ROOT, load_study, load_yaml  # noqa: E402
from engine.optimization.metrics import quality_summary  # noqa: E402
from engine.optimization.models import ZoneDecision  # noqa: E402
from engine.optimization.nsga2 import run_nsga2  # noqa: E402
from engine.optimization.objectives import build_objective_context  # noqa: E402
from engine.optimization.operators import (  # noqa: E402
    build_operator_availability,
    operator_policy,
)
from engine.optimization.pareto import pareto_sets  # noqa: E402
from engine.optimization.search import (  # noqa: E402
    decision_key,
    evaluate_candidate,
)


SCENARIOS = (
    "public_coordination",
    "development_growth",
    "resident_heritage_priority",
)

# 算子归属在研究设计中是固定的：增建类归开发主体，公共空间重构归公共资产，
# 院落通行改善归居民。它只用于"补进并集的新算子该由谁操作"，
# 不改变任一情景原有的 stakeholder_targets。
CANONICAL_TARGETS: dict[str, list[str]] = {
    "densify": ["developer"],
    "open_ground": ["developer"],
    "split_to_towers": ["developer"],
    "heritage_step_down": ["developer"],
    "public_space_reconfiguration": ["state"],
    "courtyard_access_improvement": ["resident"],
}

# 统一强度表取三个情景中该算子出现过的最高值。它是"同等强度"的操作化定义：
# 不存在于某情景的算子没有原值可用，只能取一个明确写出的共同值。
COMMON_INTENSITY: dict[str, float] = {
    "densify": 1.0,
    "open_ground": 0.75,
    "split_to_towers": 1.0,
    "heritage_step_down": 1.0,
    "public_space_reconfiguration": 1.0,
    "courtyard_access_improvement": 0.65,
}

UNION_OPERATORS = list(CANONICAL_TARGETS)

# 探针只考虑可能增加净建筑面积的算子；heritage_step_down 在单元内守恒 GFA，
# public_space_reconfiguration 与 courtyard_access_improvement 会削减 GFA。
CAPACITY_OPERATORS = ("densify", "open_ground", "split_to_towers")

ARMS: dict[str, dict[str, str]] = {
    "attr-on__ops-own__int-own": {"attribution": "on", "operator_set": "own", "intensity": "own"},
    "attr-off__ops-own__int-own": {"attribution": "off", "operator_set": "own", "intensity": "own"},
    "attr-on__ops-own__int-common": {"attribution": "on", "operator_set": "own", "intensity": "common"},
    "attr-off__ops-own__int-common": {"attribution": "off", "operator_set": "own", "intensity": "common"},
    "attr-on__ops-union__int-own": {"attribution": "on", "operator_set": "union", "intensity": "own"},
    "attr-off__ops-union__int-own": {"attribution": "off", "operator_set": "union", "intensity": "own"},
    "attr-on__ops-union__int-common": {"attribution": "on", "operator_set": "union", "intensity": "common"},
    "attr-off__ops-union__int-common": {"attribution": "off", "operator_set": "union", "intensity": "common"},
}

REFERENCE_ARM = "attr-on__ops-own__int-own"


def transform_scenario(scenario: dict[str, Any], arm: dict[str, str]) -> dict[str, Any]:
    """按因子改写 operator_policy，返回新字典，不修改入参。"""
    result = deepcopy(scenario)
    policy = result.setdefault("operator_policy", {})
    allowed = list(policy.get("allowed_operators", []))
    targets = dict(policy.get("stakeholder_targets", {}))
    limits = dict(policy.get("maximum_intensity", {}))
    before = {
        "allowed_operators": allowed,
        "stakeholder_targets": targets,
        "maximum_intensity": limits,
    }

    if not allowed:
        raise ValueError("情景缺少 operator_policy.allowed_operators，无法定义消融臂")

    if arm["operator_set"] == "union":
        for operator in UNION_OPERATORS:
            if operator not in allowed:
                allowed.append(operator)
            if operator not in limits:
                # 情景从未定义该算子的上限，取统一表中的显式值。
                limits[operator] = COMMON_INTENSITY[operator]
            if operator not in targets:
                targets[operator] = list(CANONICAL_TARGETS[operator])

    if arm["intensity"] == "common":
        limits = {operator: COMMON_INTENSITY[operator] for operator in allowed}

    if arm["attribution"] == "off":
        targets = {}

    policy["allowed_operators"] = allowed
    policy["stakeholder_targets"] = targets
    policy["maximum_intensity"] = limits
    result["operator_policy"] = policy
    return {
        "scenario": result,
        "diff": {
            "before": before,
            "after": {
                "allowed_operators": allowed,
                "stakeholder_targets": targets,
                "maximum_intensity": limits,
            },
        },
    }


def decision_rows(candidates) -> list[dict[str, Any]]:
    rows = []
    for candidate in candidates:
        decisions = [item for item in candidate.decisions if item.operator != "noop"]
        rows.append({
            "solution_id": candidate.solution_id,
            "feasible": candidate.feasible,
            "violation_count": len(candidate.violations),
            "violation_codes": ";".join(
                sorted({item.code for item in candidate.violations})
            ),
            "changed_zone_count": len({item.zone_id for item in decisions}),
            "decision_signature": ";".join(
                f"{item.zone_id}:{item.operator}:{item.intensity:.4f}"
                for item in decisions
            ),
            **candidate.objectives,
            **candidate.descriptors,
        })
    return rows


def operation_profile(candidates) -> dict[str, float]:
    """候选级算子出现率：包含该算子的候选占比。"""
    total = len(candidates) or 1
    counts: Counter[str] = Counter()
    for candidate in candidates:
        for operator in {item.operator for item in candidate.decisions if item.operator != "noop"}:
            counts[operator] += 1
    return {operator: counts[operator] / total for operator in sorted(counts)}


def summarise(candidates, pareto, metadata, objective_config) -> dict[str, Any]:
    """极值按项目既有口径（epsilon 前沿）统计，另附有效候选极值。

    前沿极值可与 E0/E1 旧表直接比较；``*_effective`` 排除现状基线，
    表示搜索在有效改动候选上实际找到的极值。
    """
    effective = [item for item in candidates if item.has_effective_change]
    feasible = [item for item in candidates if item.feasible]
    quality = quality_summary(pareto, objective_config)
    return {
        "effective": len(effective),
        "pareto": len(pareto),
        "feasible_ratio": len(feasible) / len(candidates) if candidates else 0.0,
        "max_net": max(
            (item.objectives["development_capacity"] for item in pareto), default=0.0
        ),
        "max_release": max(
            (item.objectives["street_connected_released_ground"] for item in pareto),
            default=0.0,
        ),
        "min_disruption": min(
            (item.objectives["residential_disruption"] for item in pareto), default=0.0
        ),
        "max_net_effective": max(
            (item.objectives["development_capacity"] for item in effective), default=0.0
        ),
        "max_release_effective": max(
            (item.objectives["street_connected_released_ground"] for item in effective),
            default=0.0,
        ),
        "hypervolume": quality.get("hypervolume", 0.0),
        "raw_calls": metadata.get("raw_evaluation_calls", 0),
        "cache_hits": metadata.get("cache_hits", 0),
        "candidate_operation_share": operation_profile(candidates),
        "pareto_operation_share": operation_profile(pareto),
    }


def run_nsga2_task(spec: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    study = load_study(
        spec["scenario"],
        research_demo=False,
        shared_experiment_controls=spec["control_envelope"] == "shared",
    )
    if study.blockers:
        raise RuntimeError(f"{spec['scenario']} 输入仍有阻塞项：{study.blockers}")
    transformed = transform_scenario(study.scenario, ARMS[spec["arm"]])
    study.scenario = transformed["scenario"]
    study.retain_candidate_geometries = False

    candidates, pareto, metadata = run_nsga2(
        study,
        spec["operator_specs"],
        population=spec["population"],
        generations=spec["generations"],
        seed=spec["seed"],
        evaluation_budget=spec["budget"],
        fixed_raw_budget=True,
    )
    summary = summarise(candidates, pareto, metadata, study.objective_config)
    payload = {
        "scenario": spec["scenario"],
        "arm": spec["arm"],
        "seed": spec["seed"],
        "budget": spec["budget"],
        "population": spec["population"],
        "generations": spec["generations"],
        "amplitude_arm": spec["amplitude_arm"],
        "control_envelope": spec["control_envelope"],
        "generations_executed": metadata.get("generations_executed"),
        "scenario_diff": transformed["diff"],
        "runtime_seconds": time.perf_counter() - started,
        **summary,
    }
    return {
        "kind": "nsga2",
        "scenario": spec["scenario"],
        "arm": spec["arm"],
        "seed": spec["seed"],
        "summary": payload,
        "rows": decision_rows(candidates),
        "scenario_after": study.scenario,
    }


def _decisions(zone_ids: list[str], mapping: dict[str, tuple[str, float]]) -> list[ZoneDecision]:
    return [
        ZoneDecision(zone_id, *mapping.get(zone_id, ("noop", 0.0)))
        for zone_id in zone_ids
    ]


def run_capacity_probe(
    study,
    operator_specs: dict[str, Any],
    *,
    budget: int = 320,
) -> dict[str, Any]:
    """确定性贪心饱和：逐单元筛选容量算子，再累加提交，最后用剩余预算做换入搜索。

    预算以原始 ``evaluate_candidate`` 调用计；完全确定性，不依赖随机种子。
    """
    zone_ids = sorted(study.zones["zone_id"].astype(str).unique())
    availability = build_operator_availability(
        study.buildings, study.zones, study.controls, study.scenario, operator_specs
    )
    _, _, limits = operator_policy(study.scenario)
    # 单元数上限只写在解码器里（_decode_vector），check_constraints 只检查建筑比例。
    # 探针直接构造决策，因此必须自己执行同一条上限，否则会越过情景改动范围。
    zone_ratio = float(
        study.scenario.get("implementation", {}).get("maximum_changed_zone_ratio", 0.40)
    )
    zone_cap = max(1, round(len(zone_ids) * zone_ratio))
    context = build_objective_context(
        study.buildings, study.boundary, study.streets, study.scenario, study.objective_config
    )
    cache: dict[tuple, Any] = {}
    calls = 0

    def evaluate(mapping: dict[str, tuple[str, float]]):
        nonlocal calls
        decisions = _decisions(zone_ids, mapping)
        key = decision_key(decisions)
        if key in cache:
            return cache[key]
        if calls >= budget:
            return None
        calls += 1
        candidate = evaluate_candidate(
            study, decisions, operator_specs, f"P_{calls:04d}", context
        )
        cache[key] = candidate
        return candidate

    def capacity(candidate) -> float:
        return candidate.objectives["development_capacity"]

    def changed_zone_count(candidate) -> int:
        return len({str(change.get("zone_id")) for change in candidate.changes})

    def acceptable(candidate) -> bool:
        return candidate.feasible and changed_zone_count(candidate) <= zone_cap

    baseline = evaluate({})
    best = baseline
    current: dict[str, tuple[str, float]] = {}

    # 第一轮：单单元筛选，每个单元尝试所有可用的容量算子。
    singles: list[tuple[float, str, str, float]] = []
    for zone_id in zone_ids:
        best_single = None
        for operator in CAPACITY_OPERATORS:
            if operator not in availability.get(zone_id, ()):
                continue
            candidate = evaluate({zone_id: (operator, limits.get(operator, 1.0))})
            if candidate is None:
                break
            if acceptable(candidate) and (
                best_single is None or capacity(candidate) > best_single[0]
            ):
                best_single = (capacity(candidate), operator, limits.get(operator, 1.0))
        if best_single is not None and best_single[0] > capacity(baseline) + 1e-12:
            singles.append((best_single[0], zone_id, best_single[1], best_single[2]))
    singles.sort(key=lambda item: (-item[0], item[1]))

    # 第二轮：按单单元增益从高到低累加，只接受仍可行的组合。
    committed: list[str] = []
    for _, zone_id, operator, intensity in singles:
        if calls >= budget:
            break
        trial = dict(current)
        trial[zone_id] = (operator, intensity)
        candidate = evaluate(trial)
        if candidate is None:
            break
        if acceptable(candidate) and capacity(candidate) > capacity(best) + 1e-12:
            current = trial
            committed.append(zone_id)
            best = candidate

    # 第三轮：剩余预算做换入搜索（先尝试纯增补，再尝试替换最弱的已提交单元）。
    gain_of = {zone_id: gain for gain, zone_id, _, _ in singles}
    while calls < budget:
        improved = False
        excluded = [
            (zone_id, operator, limits.get(operator, 1.0))
            for zone_id in zone_ids
            if zone_id not in current
            for operator in CAPACITY_OPERATORS
            if operator in availability.get(zone_id, ())
        ]
        for zone_id, operator, intensity in excluded:
            trial = dict(current)
            trial[zone_id] = (operator, intensity)
            candidate = evaluate(trial)
            if candidate is None:
                break
            if acceptable(candidate) and capacity(candidate) > capacity(best) + 1e-12:
                current, best, improved = trial, candidate, True
                break
        if improved:
            continue
        for zone_out in sorted(current, key=lambda zone_id: gain_of.get(zone_id, 0.0)):
            for zone_id, operator, intensity in excluded:
                if zone_id == zone_out:
                    continue
                trial = dict(current)
                trial.pop(zone_out, None)
                trial[zone_id] = (operator, intensity)
                candidate = evaluate(trial)
                if candidate is None:
                    break
                if acceptable(candidate) and capacity(candidate) > capacity(best) + 1e-12:
                    current, best, improved = trial, candidate, True
                    break
            if improved or calls >= budget:
                break
        if not improved:
            break

    changed_zone_ids = {str(change.get("zone_id")) for change in best.changes}
    zones_used = Counter(item.operator for item in best.decisions if item.operator != "noop")
    return {
        "scenario": None,
        "arm": None,
        "budget": budget,
        "calls": calls,
        "budget_exhausted": calls >= budget,
        "capacity": capacity(best),
        "release": best.objectives["street_connected_released_ground"],
        "disruption": best.objectives["residential_disruption"],
        "feasible": best.feasible,
        "zone_cap": zone_cap,
        "far": best.descriptors.get("far"),
        "coverage": best.descriptors.get("coverage"),
        "net_gfa_change_m2": best.descriptors.get("net_gfa_change_m2"),
        "gross_added_m2": best.descriptors.get("gross_added_m2"),
        # 决策数（含被夹到零的算子）与实际发生改变的单元数必须分开：
        # 只有后者受 maximum_changed_zone_ratio 约束。
        "zones_with_decisions": sum(1 for item in best.decisions if item.operator != "noop"),
        "changed_zones": len(changed_zone_ids),
        "changed_buildings": len({str(change.get("bid")) for change in best.changes}),
        "operator_counts": dict(zones_used),
        "decision_signature": ";".join(
            f"{item.zone_id}:{item.operator}:{item.intensity:.4f}"
            for item in best.decisions if item.operator != "noop"
        ),
    }


def run_probe_task(spec: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    study = load_study(
        spec["scenario"],
        research_demo=False,
        shared_experiment_controls=spec["control_envelope"] == "shared",
    )
    if study.blockers:
        raise RuntimeError(f"{spec['scenario']} 输入仍有阻塞项：{study.blockers}")
    transformed = transform_scenario(study.scenario, ARMS[spec["arm"]])
    study.scenario = transformed["scenario"]
    study.retain_candidate_geometries = False
    payload = run_capacity_probe(study, spec["operator_specs"], budget=spec["budget"])
    payload.update({
        "scenario": spec["scenario"],
        "arm": spec["arm"],
        "control_envelope": spec["control_envelope"],
        "runtime_seconds": time.perf_counter() - started,
    })
    return {
        "kind": "probe",
        "scenario": spec["scenario"],
        "arm": spec["arm"],
        "summary": payload,
        "scenario_after": study.scenario,
    }


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


def config_hashes() -> dict[str, str]:
    files = (
        "scenarios.yaml",
        "operator_specs.yaml",
        "amplitude_arms.yaml",
        "research_assumptions.yaml",
        "objectives.yaml",
        "constraints.yaml",
    )
    return {
        name: hashlib.sha256((CONFIG_ROOT / name).read_bytes()).hexdigest()
        for name in files
        if (CONFIG_ROOT / name).exists()
    }


def group_rows(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault((row["scenario"], row["arm"]), []).append(row)
    if key == "probe":
        fields = ("capacity", "release", "disruption", "calls", "changed_zones", "far")
    else:
        fields = (
            "effective", "pareto", "max_net", "max_release", "min_disruption",
            "hypervolume", "feasible_ratio",
        )
    output = []
    for (scenario, arm), items in sorted(grouped.items()):
        entry: dict[str, Any] = {
            "scenario": scenario,
            "arm": arm,
            "n": len(items),
            "seeds": ",".join(str(item.get("seed", "deterministic")) for item in items),
        }
        for field_name in fields:
            values = [float(item[field_name]) for item in items]
            entry[f"{field_name}_mean"] = statistics.mean(values)
            entry[f"{field_name}_std"] = statistics.stdev(values) if len(values) > 1 else 0.0
            entry[f"{field_name}_min"] = min(values)
            entry[f"{field_name}_max"] = max(values)
        output.append(entry)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", default="11,23,37")
    parser.add_argument("--scenarios", default=",".join(SCENARIOS))
    parser.add_argument("--arms", default=",".join(ARMS))
    parser.add_argument("--population", type=int, default=16)
    parser.add_argument("--generations", type=int, default=20)
    parser.add_argument("--budget", type=int, default=320,
                        help="每次 run 的固定原始评价次数（NSGA-II 与探针共用）")
    parser.add_argument("--probe-budget", type=int, default=None,
                        help="容量探针预算，缺省与 --budget 相同")
    parser.add_argument("--amplitude-arm", default=None)
    parser.add_argument("--control-envelope", choices=("shared", "frozen_per_zone"),
                        default="shared")
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--probe", action="store_true", help="同时运行容量探针")
    parser.add_argument("--only", choices=("nsga2", "probe"), default=None)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    seeds = [int(value.strip()) for value in args.seeds.split(",") if value.strip()]
    scenarios = [value.strip() for value in args.scenarios.split(",") if value.strip()]
    arm_ids = [value.strip() for value in args.arms.split(",") if value.strip()]
    for name in (*scenarios, *arm_ids):
        if name not in SCENARIOS and name not in ARMS:
            raise KeyError(f"未知情景或臂：{name}")

    output: Path = args.output
    if output.exists() and any(output.iterdir()) and not args.overwrite:
        raise SystemExit(f"输出目录非空：{output}（需要 --overwrite 才覆盖）")
    output.mkdir(parents=True, exist_ok=True)

    arm_id, arm = resolve_arm(args.amplitude_arm)
    operator_specs = apply_operator_arm(
        load_yaml(CONFIG_ROOT / "operator_specs.yaml").get("operators", {}), arm
    )
    probe_budget = args.probe_budget or args.budget

    tasks: list[dict[str, Any]] = []
    run_nsga2_here = args.only != "probe"
    run_probe_here = (args.probe or args.only == "probe") and args.only != "nsga2"
    if run_nsga2_here:
        for scenario in scenarios:
            for arm_name in arm_ids:
                for seed in seeds:
                    tasks.append({
                        "kind": "nsga2", "scenario": scenario, "arm": arm_name, "seed": seed,
                        "population": args.population, "generations": args.generations,
                        "budget": args.budget, "operator_specs": operator_specs,
                        "amplitude_arm": arm_id,
                        "control_envelope": args.control_envelope,
                    })
    if run_probe_here:
        for scenario in scenarios:
            for arm_name in arm_ids:
                tasks.append({
                    "kind": "probe", "scenario": scenario, "arm": arm_name, "seed": None,
                    "budget": probe_budget, "operator_specs": operator_specs,
                    "amplitude_arm": arm_id,
                    "control_envelope": args.control_envelope,
                })

    started = time.perf_counter()
    summaries: list[dict[str, Any]] = []
    probes: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    scenario_snapshots: dict[str, dict[str, Any]] = {}

    def record(result: dict[str, Any]) -> None:
        scenario, arm_name = result["scenario"], result["arm"]
        if result.get("scenario_after") is not None:
            scenario_snapshots.setdefault(scenario, {})[arm_name] = result["scenario_after"]
        if result["kind"] == "nsga2":
            seed = result["seed"]
            run_dir = output / "runs" / scenario / arm_name / f"seed_{seed}"
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "summary.json").write_text(
                json.dumps(result["summary"], ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            write_csv(run_dir / "candidates.csv", result["rows"])
            summaries.append(result["summary"])
            print(
                f"[{len(summaries)}/{len(tasks)}] {scenario} {arm_name} seed={seed} "
                f"eff={result['summary']['effective']} "
                f"pareto={result['summary']['pareto']} "
                f"max_net={100 * result['summary']['max_net']:.3f}% "
                f"({result['summary']['runtime_seconds']:.0f}s)",
                flush=True,
            )
        else:
            probe_dir = output / "probes" / scenario
            probe_dir.mkdir(parents=True, exist_ok=True)
            (probe_dir / f"{arm_name}.json").write_text(
                json.dumps(result["summary"], ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            probes.append(result["summary"])
            print(
                f"[probe {len(probes)}] {scenario} {arm_name} "
                f"capacity={100 * result['summary']['capacity']:.3f}% "
                f"calls={result['summary']['calls']} "
                f"({result['summary']['runtime_seconds']:.0f}s)",
                flush=True,
            )

    if tasks:
        if args.jobs <= 1:
            for spec in tasks:
                try:
                    record(run_nsga2_task(spec) if spec["kind"] == "nsga2" else run_probe_task(spec))
                except Exception as error:  # noqa: BLE001 - 逐 run 记录失败，不中断整批
                    failures.append({**spec, "operator_specs": None, "error": repr(error)})
                    print(f"FAILED {spec['kind']} {spec['scenario']} {spec['arm']}: {error}",
                          file=sys.stderr, flush=True)
        else:
            with ProcessPoolExecutor(max_workers=args.jobs) as pool:
                futures = {
                    pool.submit(
                        run_nsga2_task if spec["kind"] == "nsga2" else run_probe_task, spec
                    ): spec
                    for spec in tasks
                }
                for future in as_completed(futures):
                    spec = futures[future]
                    try:
                        record(future.result())
                    except Exception as error:  # noqa: BLE001
                        failures.append({**spec, "operator_specs": None, "error": repr(error)})
                        print(
                            f"FAILED {spec['kind']} {spec['scenario']} {spec['arm']}: {error}",
                            file=sys.stderr, flush=True,
                        )

    write_csv(output / "summary.csv", summaries)
    write_csv(output / "aggregate_summary.csv", group_rows(summaries, "nsga2"))
    if probes:
        write_csv(output / "probe_summary.csv", probes)
        write_csv(output / "probe_aggregate.csv", group_rows(probes, "probe"))
    if failures:
        (output / "failures.json").write_text(
            json.dumps(failures, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    manifest = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "script": str(Path(__file__).relative_to(WS05)),
        "study": "dapuqiao",
        "scenarios": scenarios,
        "seeds": seeds,
        "arms": {name: ARMS[name] for name in arm_ids},
        "reference_arm": REFERENCE_ARM,
        "amplitude_arm": arm_metadata(arm_id, arm),
        "control_envelope": args.control_envelope,
        "implementation_scope_held_constant": True,
        "heritage_freeze_held_constant": True,
        "budget": {
            "nsga2_raw_calls": args.budget,
            "population": args.population,
            "generations": args.generations,
            "probe_raw_calls": probe_budget,
            "fixed_raw_budget": True,
        },
        "arm_semantics": {
            "attribution": "stakeholder_targets 保留/清空；editable = stakeholder != state 这一结构层闸门不动",
            "operator_set": "allowed_operators 情景原值/六算子并集；新增算子的强度取统一表并记入 scenario_diff",
            "intensity": "maximum_intensity 情景原值/统一表（三情景该算子最高值）",
        },
        "probe_semantics": (
            "确定性贪心饱和搜索：单单元容量算子筛选 → 按增益累加 → 剩余预算换入；"
            "只测容量可达上限，不与 NSGA-II 前沿质量比较"
        ),
        "scenario_snapshots": scenario_snapshots,
        "config_sha256": config_hashes(),
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "pymoo": package_metadata.version("pymoo"),
            "geopandas": package_metadata.version("geopandas"),
            "pandas": package_metadata.version("pandas"),
            "numpy": package_metadata.version("numpy"),
        },
        "elapsed_seconds": time.perf_counter() - started,
        "run_count": len(summaries),
        "probe_count": len(probes),
        "failure_count": len(failures),
        "statutory_planning_result": False,
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    print(f"\n完成：{output} ({len(summaries)} runs, {len(probes)} probes, "
          f"{len(failures)} failures, {manifest['elapsed_seconds'] / 60:.1f} min)")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())

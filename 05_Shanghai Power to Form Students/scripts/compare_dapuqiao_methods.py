#!/usr/bin/env python3
"""Compare one conventional parameter baseline with four governance scenarios."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402


WS05 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WS05))

from engine.optimization.data import CONFIG_ROOT, load_study, load_yaml  # noqa: E402
from engine.optimization.metrics import (  # noqa: E402
    coverage,
    front_distribution,
    front_metrics,
    holm_adjust,
    paired_wilcoxon,
)
from engine.optimization.models import CandidateEvaluation  # noqa: E402
from engine.optimization.nsga2 import run_nsga2  # noqa: E402
from engine.optimization.parameter_baseline import (  # noqa: E402
    build_parameter_baseline_study,
    run_parameter_baseline,
)
from engine.optimization.roles import evaluate_role_sensitivity, evaluate_roles  # noqa: E402
from run_dapuqiao_optimization import (  # noqa: E402
    export_run,
    git_metadata,
    input_scope_metadata,
    runtime_metadata,
    snapshot_code,
    snapshot_inputs,
)


SCENARIOS = (
    "tourism_capture",
    "everyday_life_first",
    "heritage_micro_economy",
    "negotiated_24h_alley",
)
BASELINE_ID = "conventional_parameter_baseline"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", default="11,23,37,53,71")
    parser.add_argument("--population", type=int, default=20)
    parser.add_argument("--generations", type=int, default=20)
    parser.add_argument("--evaluation-budget", type=int)
    parser.add_argument(
        "--jobs", type=int, default=1,
        help="按随机种子并行的进程数；每个种子内部仍顺序运行五种方法",
    )
    parser.add_argument(
        "--research-demo", action="store_true",
        help="仅在规范输入缺失时使用草稿研究假设；默认读取已冻结的规范研究输入",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--skip-geometries", action="store_true",
                        help="仅用于快速管线检查；正式论文运行不要使用")
    return parser.parse_args()


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def lightweight(candidate) -> CandidateEvaluation:
    return CandidateEvaluation(
        solution_id=candidate.solution_id,
        decisions=[],
        buildings=None,
        changes=[],
        objectives=dict(candidate.objectives),
        descriptors=dict(candidate.descriptors),
        violations=list(candidate.violations),
    )


def base_summary(seed, method_id, candidates, front, metadata, runtime_seconds):
    feasible = [candidate for candidate in candidates if candidate.feasible]
    violation_counts = Counter(
        violation.code for candidate in candidates for violation in candidate.violations
    )
    return {
        "seed": seed,
        "method_id": method_id,
        "effective_evaluation_budget": metadata["effective_evaluation_budget"],
        "candidate_count_including_current": len(candidates),
        "feasible_count": len(feasible),
        "feasible_ratio": len(feasible) / len(candidates) if candidates else 0.0,
        "pareto_count": len(front),
        "minimum_residential_disruption": min(
            candidate.objectives["residential_disruption"] for candidate in front
        ),
        "maximum_development_capacity": max(
            candidate.objectives["development_capacity"] for candidate in front
        ),
        "maximum_released_ground": max(
            candidate.objectives["street_connected_released_ground"] for candidate in front
        ),
        "runtime_seconds": runtime_seconds,
        "violation_counts": json.dumps(violation_counts, ensure_ascii=False, sort_keys=True),
        "generations_executed": metadata["generations_executed"],
        "raw_unique_evaluations": metadata["raw_unique_evaluations"],
        "cache_hits": metadata["cache_hits"],
    }


def controls_signature(study) -> list[dict]:
    columns = ["zone_id", "height_limit_m", "max_far", "max_coverage_ratio"]
    return (
        study.controls[columns]
        .sort_values("zone_id")
        .round(9)
        .to_dict(orient="records")
    )


def comparison_metric_config(study, baseline_config: dict) -> dict:
    """Pre-search, data-derived bounds that contain both generation methods."""
    config = deepcopy(study.objective_config)
    site_area = float(study.boundary.geometry.union_all().area)
    baseline_gfa = float(
        (study.buildings.geometry.area * study.buildings["height_m"] / 3.5).sum()
    )
    baseline_union_area = float(study.buildings.geometry.union_all().area)
    parameters = baseline_config["baseline"]["parameters"]
    maximum_height_gain = float(parameters["height_multiplier"]["max"]) - 1.0
    maximum_footprint_release = 1.0 - float(parameters["footprint_ratio"]["min"])
    config["normalization_reference"] = {
        "residential_disruption": {"minimum": 0.0, "maximum": 1.0},
        "development_capacity": {
            "minimum": 0.0,
            "maximum": maximum_height_gain * baseline_gfa / site_area,
        },
        "street_connected_released_ground": {
            "minimum": 0.0,
            "maximum": maximum_footprint_release * baseline_union_area / site_area,
        },
    }
    config["normalization_basis"] = (
        "computed before search from the shared baseline city and declared parameter maxima"
    )
    return config


def aggregate(rows: list[dict], keys: list[str]) -> list[dict]:
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["method_id"]].append(row)
    output = []
    for method_id, items in grouped.items():
        summary = {"method_id": method_id, "seed_count": len(items)}
        for key in keys:
            values = [float(item[key]) for item in items]
            summary[f"{key}_mean"] = statistics.mean(values)
            summary[f"{key}_std"] = statistics.stdev(values) if len(values) > 1 else 0.0
        output.append(summary)
    order = {name: index for index, name in enumerate((BASELINE_ID, *SCENARIOS))}
    return sorted(output, key=lambda row: order[row["method_id"]])


def plot_pareto(path: Path, records: list[dict]) -> None:
    methods = (BASELINE_ID, *SCENARIOS)
    labels = {
        BASELINE_ID: "Parameter baseline",
        "tourism_capture": "Tourism capture",
        "everyday_life_first": "Everyday life",
        "heritage_micro_economy": "Heritage micro-economy",
        "negotiated_24h_alley": "Negotiated 24h alley",
    }
    figure, axes = plt.subplots(1, 5, figsize=(18, 3.8), sharex=True, sharey=True)
    scatter = None
    for axis, method_id in zip(axes, methods):
        for record in records:
            if record["method_id"] != method_id:
                continue
            front = record["front"]
            scatter = axis.scatter(
                [item.objectives["development_capacity"] for item in front],
                [item.objectives["street_connected_released_ground"] for item in front],
                c=[item.objectives["residential_disruption"] for item in front],
                cmap="viridis", vmin=0.0, vmax=1.0, s=18, alpha=0.7,
            )
        axis.set_title(labels[method_id], fontsize=9)
        axis.set_xlabel("Development capacity")
        axis.grid(alpha=0.2)
    axes[0].set_ylabel("Street-connected released-ground potential")
    if scatter is not None:
        color_axis = figure.add_axes([0.925, 0.24, 0.012, 0.52])
        figure.colorbar(scatter, cax=color_axis, label="Residential disruption")
    figure.suptitle(
        "Pareto fronts across seeds · street-network potential; public-space context excluded"
    )
    figure.subplots_adjust(left=0.055, right=0.90, bottom=0.18, top=0.82, wspace=0.22)
    figure.savefig(path, dpi=180)
    plt.close(figure)


def plot_quality(path: Path, aggregate_rows: list[dict]) -> None:
    labels = [row["method_id"].replace("_", "\n") for row in aggregate_rows]
    x = np.arange(len(labels))
    figure, axes = plt.subplots(1, 2, figsize=(12, 4.2))
    for axis, metric, title in (
        (axes[0], "hypervolume", "Hypervolume · higher is better"),
        (axes[1], "spacing", "Spacing · lower is more even"),
    ):
        means = [row[f"{metric}_mean"] for row in aggregate_rows]
        errors = [row[f"{metric}_std"] for row in aggregate_rows]
        axis.bar(x, means, yerr=errors, color="#4C78A8", alpha=0.85, capsize=3)
        axis.set_xticks(x, labels, fontsize=8)
        axis.set_title(title)
        axis.set_ylim(bottom=0)
        axis.grid(axis="y", alpha=0.2)
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def plot_coverage(path: Path, rows: list[dict]) -> None:
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["scenario_id"]].append(row)
    scenarios = list(SCENARIOS)
    forward = [statistics.mean(item["scenario_over_baseline"] for item in grouped[name]) for name in scenarios]
    reverse = [statistics.mean(item["baseline_over_scenario"] for item in grouped[name]) for name in scenarios]
    x = np.arange(len(scenarios))
    figure, axis = plt.subplots(figsize=(10, 4.5))
    axis.bar(x - 0.18, forward, 0.36, label="C(scenario, baseline)", color="#59A14F")
    axis.bar(x + 0.18, reverse, 0.36, label="C(baseline, scenario)", color="#E15759")
    axis.set_xticks(x, [name.replace("_", "\n") for name in scenarios], fontsize=8)
    axis.set_ylim(0, 1)
    axis.set_ylabel("Dominated share")
    axis.legend()
    axis.grid(axis="y", alpha=0.2)
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def statistical_tests(summary_rows: list[dict]) -> list[dict]:
    metrics = (
        ("hypervolume", True, "primary"),
        ("feasible_ratio", True, "diagnostic"),
        ("minimum_residential_disruption", False, "diagnostic"),
        ("maximum_development_capacity", True, "diagnostic"),
        ("maximum_released_ground", True, "diagnostic"),
        ("spacing", False, "diagnostic"),
    )
    by_key = {
        (int(row["seed"]), row["method_id"]): row for row in summary_rows
    }
    seeds = sorted({int(row["seed"]) for row in summary_rows})
    rows = []
    for metric, higher_is_better, role in metrics:
        metric_rows = []
        for scenario_id in SCENARIOS:
            baseline_values = [
                float(by_key[(seed, BASELINE_ID)][metric]) for seed in seeds
            ]
            scenario_values = [
                float(by_key[(seed, scenario_id)][metric]) for seed in seeds
            ]
            metric_rows.append({
                "scenario_id": scenario_id,
                "baseline_id": BASELINE_ID,
                "metric": metric,
                "metric_role": role,
                "higher_is_better": higher_is_better,
                **paired_wilcoxon(
                    baseline_values, scenario_values,
                    higher_is_better=higher_is_better,
                ),
            })
        adjusted = holm_adjust([
            float(row["p_value_two_sided"]) for row in metric_rows
        ])
        for row, p_value in zip(metric_rows, adjusted):
            row["p_value_holm_across_four_scenarios"] = p_value
            row["small_sample_caution"] = (
                "five paired seeds have low power; interpret effect direction, raw values, "
                "coverage and convergence together"
            )
        rows.extend(metric_rows)
    return rows


def run_seed_worker(
    seed: int,
    *,
    research_demo: bool,
    population: int,
    generations: int,
    budget: int,
    runs_root: Path,
    skip_geometries: bool,
) -> tuple[list[dict], list[str]]:
    """Run all five methods for one seed in an isolated process."""
    specs = load_yaml(CONFIG_ROOT / "operator_specs.yaml").get("operators", {})
    roles = load_yaml(CONFIG_ROOT / "role_profiles.yaml")
    baseline_config = load_yaml(CONFIG_ROOT / "parameter_baseline.yaml")
    studies = {
        scenario_id: load_study(
            scenario_id,
            research_demo=research_demo,
            shared_experiment_controls=True,
        )
        for scenario_id in SCENARIOS
    }
    blockers = {
        scenario_id: study.blockers
        for scenario_id, study in studies.items()
        if study.blockers
    }
    if blockers:
        raise RuntimeError(f"seed={seed} 规范研究输入仍有阻塞项：{blockers}")
    signature = controls_signature(studies[SCENARIOS[0]])
    shared_defaults = studies[SCENARIOS[0]].scenario["defaults"]
    for scenario_id, study in studies.items():
        if controls_signature(study) != signature:
            raise RuntimeError(f"seed={seed} {scenario_id} 未使用共同硬约束")
        for key in (
            "height_limit_m", "max_far", "max_coverage_ratio",
            "minimum_residential_retention",
        ):
            if study.scenario["defaults"].get(key) != shared_defaults.get(key):
                raise RuntimeError(f"seed={seed} {scenario_id} 的共同口径 {key} 不一致")

    baseline_study = build_parameter_baseline_study(
        studies[SCENARIOS[0]], baseline_config
    )
    objective_config = comparison_metric_config(
        studies[SCENARIOS[0]], baseline_config
    )
    records = []
    messages = []
    run_plan = [(BASELINE_ID, baseline_study), *[
        (scenario_id, studies[scenario_id]) for scenario_id in SCENARIOS
    ]]
    for method_id, study in run_plan:
        started = time.perf_counter()
        if method_id == BASELINE_ID:
            candidates, front, metadata = run_parameter_baseline(
                study, baseline_config, population=population,
                generations=generations, seed=seed, evaluation_budget=budget,
            )
            role_rows, selections, sensitivity_rows = [], {}, []
        else:
            candidates, front, metadata = run_nsga2(
                study, specs, population=population,
                generations=generations, seed=seed, evaluation_budget=budget,
            )
            reference = study.objective_config.get("normalization_reference", {})
            role_rows, selections = evaluate_roles(front, roles, reference)
            sensitivity_rows = evaluate_role_sensitivity(front, roles, reference)
        runtime_seconds = time.perf_counter() - started
        if metadata.get("effective_evaluation_budget") != budget:
            raise RuntimeError(f"{method_id} seed={seed} 的有效评价预算不一致")
        run_output = runs_root / method_id / f"seed_{seed}"
        export_run(
            study, candidates, front, role_rows, selections,
            seed=seed, samples=0, search_metadata=metadata,
            output_dir=run_output, method_id=method_id,
            export_geometries=not skip_geometries,
            role_sensitivity_rows=sensitivity_rows,
            quality_config=objective_config,
            optimization_runtime_seconds=runtime_seconds,
        )
        records.append({
            "seed": seed,
            "method_id": method_id,
            "front": [lightweight(item) for item in front],
            "summary": base_summary(
                seed, method_id, candidates, front, metadata, runtime_seconds
            ),
        })
        messages.append(
            f"seed={seed} {method_id}: {budget} independent evaluations, "
            f"{len(front)} Pareto, {runtime_seconds:.1f}s"
        )
        del candidates, front
    return records, messages


def main() -> int:
    args = parse_args()
    seeds = [int(value.strip()) for value in args.seeds.split(",") if value.strip()]
    if not seeds or args.population < 2 or args.generations < 1 or args.jobs < 1:
        raise ValueError("seeds、population、generations 和 jobs 必须为正")
    budget = args.evaluation_budget or args.population * args.generations
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = args.output or WS05 / "out" / "dapuqiao" / "method_comparison" / stamp
    output = output.resolve()
    runs_root = output / "runs"
    runs_root.mkdir(parents=True, exist_ok=True)

    baseline_config = load_yaml(CONFIG_ROOT / "parameter_baseline.yaml")
    studies = {
        scenario_id: load_study(
            scenario_id,
            research_demo=args.research_demo,
            shared_experiment_controls=True,
        )
        for scenario_id in SCENARIOS
    }
    blockers = {
        scenario_id: study.blockers
        for scenario_id, study in studies.items()
        if study.blockers
    }
    if blockers:
        raise RuntimeError(
            f"规范研究输入仍有阻塞项：{blockers}。"
            "仅调试草稿管线时可显式加 --research-demo。"
        )
    signature = controls_signature(studies[SCENARIOS[0]])
    shared_defaults = studies[SCENARIOS[0]].scenario["defaults"]
    for scenario_id, study in studies.items():
        if controls_signature(study) != signature:
            raise RuntimeError(f"{scenario_id} 未使用共同硬约束")
        for key in (
            "height_limit_m", "max_far", "max_coverage_ratio",
            "minimum_residential_retention",
        ):
            if study.scenario["defaults"].get(key) != shared_defaults.get(key):
                raise RuntimeError(f"{scenario_id} 的共同口径 {key} 不一致")
    objective_config = comparison_metric_config(
        studies[SCENARIOS[0]], baseline_config
    )

    records = []
    worker_count = min(args.jobs, len(seeds))
    worker_kwargs = {
        "research_demo": args.research_demo,
        "population": args.population,
        "generations": args.generations,
        "budget": budget,
        "runs_root": runs_root,
        "skip_geometries": args.skip_geometries,
    }
    if worker_count == 1:
        for seed in seeds:
            seed_records, messages = run_seed_worker(seed, **worker_kwargs)
            records.extend(seed_records)
            for message in messages:
                print(message, flush=True)
    else:
        with ProcessPoolExecutor(max_workers=worker_count) as executor:
            futures = {
                executor.submit(run_seed_worker, seed, **worker_kwargs): seed
                for seed in seeds
            }
            for future in as_completed(futures):
                seed = futures[future]
                try:
                    seed_records, messages = future.result()
                except Exception as error:
                    raise RuntimeError(f"seed={seed} 并行运行失败") from error
                records.extend(seed_records)
                for message in messages:
                    print(message, flush=True)
    method_order = {
        method_id: index for index, method_id in enumerate((BASELINE_ID, *SCENARIOS))
    }
    records.sort(key=lambda row: (int(row["seed"]), method_order[row["method_id"]]))

    summary_rows = []
    for record in records:
        row = dict(record["summary"])
        row.update(front_metrics(record["front"], objective_config))
        summary_rows.append(row)

    coverage_rows = []
    indexed = {(record["seed"], record["method_id"]): record for record in records}
    for seed in seeds:
        baseline_front = indexed[(seed, BASELINE_ID)]["front"]
        for scenario_id in SCENARIOS:
            scenario_front = indexed[(seed, scenario_id)]["front"]
            coverage_rows.append({
                "seed": seed,
                "scenario_id": scenario_id,
                "scenario_over_baseline": coverage(scenario_front, baseline_front),
                "baseline_over_scenario": coverage(baseline_front, scenario_front),
                "scenario_pareto_count": len(scenario_front),
                "baseline_pareto_count": len(baseline_front),
            })

    fairness_rows = []
    for row in summary_rows:
        effective = int(row["effective_evaluation_budget"])
        candidate_count = int(row["candidate_count_including_current"])
        fairness_rows.append({
            "seed": row["seed"],
            "method_id": row["method_id"],
            "requested_effective_budget": budget,
            "reported_effective_budget": effective,
            "candidate_count_including_current": candidate_count,
            "expected_candidate_count_including_current": budget + 1,
            "effective_budget_match": effective == budget,
            "candidate_count_match": candidate_count == budget + 1,
        })
    if not all(
        row["effective_budget_match"] and row["candidate_count_match"]
        for row in fairness_rows
    ):
        raise RuntimeError("至少一个方法/种子未满足共同有效独立评价预算")

    statistics_rows = statistical_tests(summary_rows)

    aggregate_keys = [
        "feasible_ratio", "pareto_count", "minimum_residential_disruption",
        "maximum_development_capacity", "maximum_released_ground",
        "runtime_seconds", "hypervolume", "spacing",
    ]
    aggregate_rows = aggregate(summary_rows, aggregate_keys)
    write_csv(output / "run_summary.csv", summary_rows)
    write_csv(output / "aggregate_summary.csv", aggregate_rows)
    write_csv(output / "baseline_scenario_coverage.csv", coverage_rows)
    write_csv(output / "fairness_audit.csv", fairness_rows)
    write_csv(output / "paired_statistical_tests.csv", statistics_rows)
    distribution_rows = []
    for record in records:
        distribution_rows.extend({
            "seed": record["seed"],
            "method_id": record["method_id"],
            **row,
        } for row in front_distribution(record["front"], "epsilon_filtered"))
    write_csv(output / "pareto_distribution.csv", distribution_rows)
    plot_pareto(output / "pareto_fronts.png", records)
    plot_quality(output / "quality_metrics.png", aggregate_rows)
    plot_coverage(output / "dominance_coverage.png", coverage_rows)

    manifest = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "study": "dapuqiao",
        "methods": [BASELINE_ID, *SCENARIOS],
        "seeds": seeds,
        "population": args.population,
        "requested_generations": args.generations,
        "effective_independent_evaluation_budget": budget,
        "parallel_execution": {
            "unit": "random_seed",
            "requested_jobs": args.jobs,
            "used_processes": worker_count,
            "methods_within_seed": "sequential",
            "aggregation_order": "seed_then_method",
        },
        "common_input_data": True,
        "common_objectives": [
            "residential_disruption",
            "development_capacity",
            "street_connected_released_ground",
        ],
        "common_hard_constraints": {
            key: shared_defaults[key] for key in (
                "height_limit_m", "max_far", "max_coverage_ratio",
                "minimum_residential_retention",
            )
        },
        "common_hard_constraint_checks": [
            "geometry_validity", "study_boundary", "heritage_unchanged",
            "height_limit", "zone_far", "zone_coverage",
            "residential_retention", "new_overlap",
        ],
        "common_objective_measurement": {
            "street_access_buffer_m": objective_config.get("measurement", {}).get(
                "street_access_buffer_m", 5.0
            ),
            "floor_height_m": objective_config.get("measurement", {}).get(
                "floor_height_m", 3.5
            ),
        },
        "objective_interpretation": input_scope_metadata()["third_objective"],
        "documented_exclusions": {
            key: value for key, value in input_scope_metadata().items()
            if key != "third_objective"
        },
        "parameter_baseline": baseline_config["baseline"],
        "normalization": {
            "basis": objective_config["normalization_basis"],
            "reference_bounds": objective_config.get("normalization_reference", {}),
            "hypervolume_reference": [1.1, 1.1, 1.1],
        },
        "coverage_definition": "C(A,B) is the fraction of B's Pareto front dominated by A.",
        "statistical_analysis": {
            "paired_unit": "random seed",
            "test": "two-sided paired Wilcoxon signed-rank",
            "effect_size": "matched-pairs rank-biserial correlation; positive favors scenario",
            "multiplicity": "Holm correction across four scenario-vs-baseline tests per metric",
            "primary_metric": "hypervolume",
            "caution": "Five paired seeds have low power; report raw seed values and effect sizes.",
        },
        "random_search_role": "algorithm appendix only; run compare_dapuqiao_search.py",
        "input_mode": "research_demo" if args.research_demo else "canonical_research_inputs",
        "research_demo": args.research_demo,
        "statutory_planning_result": False,
        "geometries_exported": not args.skip_geometries,
        "reproducibility": {
            "input_files": snapshot_inputs(output),
            "code_files": snapshot_code(output),
            "git": git_metadata(),
            "runtime": runtime_metadata(),
        },
    }
    (output / "experiment_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    report = [
        "# 打浦桥传统参数基线与四治理情景对照", "",
        f"- 随机种子：{', '.join(map(str, seeds))}",
        f"- 每方法/种子有效独立评价预算：{budget}",
        "- 共同控制基线：36 m、FAR 3.0、覆盖率 0.60、住宅 GFA 保留 0.80；现状超过基线时保留现状下限；共同目标测量使用 5 m 街道缓冲",
        "- 参数基线：高度倍率 1.00–1.30；足迹保留率 0.75–1.00；不读取主体类别或情景许可",
        "- 第三目标：仅由建筑足迹变化与 5 m 道路缓冲计算临街释放地面潜力；不读取公共空间背景对象，不表示面积、权属或可达性",
        "- 排除项分开记录：4 条范围未决历史记录不进入遗产硬约束；32 栋未匹配分区建筑作为不可编辑背景",
        f"- 输入模式：{'草稿研究假设' if args.research_demo else '已冻结规范研究输入'}",
        "- 结果性质：论文研究实验，不是法定规划结果", "",
        "详见 `aggregate_summary.csv`、`baseline_scenario_coverage.csv`、`fairness_audit.csv`、`paired_statistical_tests.csv` 和三张 PNG 图。", "",
    ]
    (output / "README.md").write_text("\n".join(report), encoding="utf-8")
    try:
        display_output = output.relative_to(WS05)
    except ValueError:
        display_output = output
    print(f"输出：{display_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

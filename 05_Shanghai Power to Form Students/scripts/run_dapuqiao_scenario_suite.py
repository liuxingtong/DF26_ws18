#!/usr/bin/env python3
"""Run the three current Dapuqiao governance scenarios with one equal NSGA-II budget."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path


WS05 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WS05))

from engine.optimization.data import CONFIG_ROOT, load_study, load_yaml  # noqa: E402
from engine.optimization.nsga2 import run_nsga2  # noqa: E402
from engine.optimization.metrics import quality_summary  # noqa: E402
from engine.optimization.roles import (  # noqa: E402
    evaluate_role_priority_sensitivity,
    evaluate_roles,
)
from run_dapuqiao_optimization import (  # noqa: E402
    export_run,
    git_metadata,
    input_scope_metadata,
    runtime_metadata,
    snapshot_code,
    snapshot_inputs,
)


SCENARIOS = (
    "public_coordination",
    "development_growth",
    "resident_heritage_priority",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--population", type=int, default=20)
    parser.add_argument("--generations", type=int, default=15)
    parser.add_argument("--seeds", default="11,23,37,53,71")
    parser.add_argument(
        "--research-demo", action="store_true",
        help="仅在规范输入缺失时使用草稿研究假设",
    )
    args = parser.parse_args()
    operator_specs = load_yaml(CONFIG_ROOT / "operator_specs.yaml").get("operators", {})
    role_config = load_yaml(CONFIG_ROOT / "role_profiles.yaml")

    seeds = [int(value.strip()) for value in args.seeds.split(",") if value.strip()]
    if not seeds:
        raise ValueError("seeds 不能为空")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suite_root = WS05 / "out" / "dapuqiao" / "scenario_suites" / stamp
    suite_root.mkdir(parents=True, exist_ok=True)
    summary_rows = []
    for scenario_id in SCENARIOS:
        for seed in seeds:
            study = load_study(scenario_id, research_demo=args.research_demo)
            if study.blockers:
                raise RuntimeError(
                    f"{scenario_id} 规范研究输入仍有阻塞项：{study.blockers}"
                )
            started = time.perf_counter()
            candidates, pareto, metadata = run_nsga2(
                study,
                operator_specs,
                population=args.population,
                generations=args.generations,
                seed=seed,
            )
            epsilon = study.objective_config.get("epsilon", {})
            role_rows, selections = evaluate_roles(pareto, role_config, epsilon)
            sensitivity_rows = evaluate_role_priority_sensitivity(
                pareto, role_config, epsilon
            )
            optimization_runtime_seconds = time.perf_counter() - started
            output = export_run(
                study,
                candidates,
                pareto,
                role_rows,
                selections,
                seed=seed,
                samples=0,
                search_metadata=metadata,
                output_dir=suite_root / scenario_id / f"seed_{seed}",
                role_priority_sensitivity_rows=sensitivity_rows,
                optimization_runtime_seconds=optimization_runtime_seconds,
            )
            summary_rows.append({
                "scenario": scenario_id,
                "seed": seed,
                "effective_independent_evaluations": metadata["effective_evaluation_budget"],
                "feasible_count": sum(item.feasible for item in candidates),
                "optimization_runtime_seconds": optimization_runtime_seconds,
                **quality_summary(pareto, study.objective_config),
            })
            print(
                f"{scenario_id} seed={seed}: {len(candidates)} candidates, "
                f"{len(pareto)} epsilon-Pareto, {output.relative_to(WS05)}"
            )
    with (suite_root / "suite_summary.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary_rows[0]))
        writer.writeheader()
        writer.writerows(summary_rows)
    grouped = defaultdict(list)
    for row in summary_rows:
        grouped[row["scenario"]].append(row)
    aggregate_rows = []
    for scenario_id, items in grouped.items():
        aggregate = {"scenario": scenario_id, "seed_count": len(items)}
        for key in (
            "feasible_count", "pareto_count", "hypervolume", "spacing",
            "optimization_runtime_seconds",
        ):
            values = [float(item[key]) for item in items]
            aggregate[f"{key}_mean"] = statistics.mean(values)
            aggregate[f"{key}_std"] = statistics.stdev(values) if len(values) > 1 else 0.0
        aggregate_rows.append(aggregate)
    with (suite_root / "suite_aggregate.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(aggregate_rows[0]))
        writer.writeheader()
        writer.writerows(aggregate_rows)
    (suite_root / "suite_manifest.json").write_text(
        json.dumps({
            "scenarios": list(SCENARIOS),
            "seeds": seeds,
            "population": args.population,
            "generations": args.generations,
            "shared_objective_measurement": True,
            "shared_role_epsilon": True,
            "role_preference_model": "epsilon_tiered_lexicographic",
            "objective_measurement": study.objective_config.get("measurement", {}),
            "epsilon": study.objective_config.get("epsilon", {}),
            "normalization_reference": study.objective_config.get(
                "normalization_reference", {}
            ),
            "input_mode": "research_demo" if args.research_demo else "canonical_research_inputs",
            "research_demo": args.research_demo,
            "statutory_planning_result": False,
            "objective_interpretation": input_scope_metadata()["third_objective"],
            "documented_exclusions": {
                key: value for key, value in input_scope_metadata().items()
                if key != "third_objective"
            },
            "reproducibility": {
                "input_files": snapshot_inputs(suite_root),
                "code_files": snapshot_code(suite_root),
                "git": git_metadata(),
                "runtime": runtime_metadata(),
            },
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"汇总：{suite_root.relative_to(WS05)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

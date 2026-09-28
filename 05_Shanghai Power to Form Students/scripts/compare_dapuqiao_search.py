#!/usr/bin/env python3
"""Compare NSGA-II with an equal-budget random search under fixed assumptions."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path


WS05 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WS05))

from engine.optimization.data import CONFIG_ROOT, load_study, load_yaml  # noqa: E402
from engine.optimization.metrics import (  # noqa: E402
    coverage,
    quality_summary,
)
from engine.optimization.nsga2 import run_nsga2  # noqa: E402
from engine.optimization.search import run_random_baseline  # noqa: E402
from run_dapuqiao_optimization import (  # noqa: E402
    git_metadata,
    input_scope_metadata,
    runtime_metadata,
    snapshot_code,
    snapshot_inputs,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", default="tourism_capture")
    parser.add_argument("--seeds", default="11,23,37")
    parser.add_argument("--population", type=int, default=20)
    parser.add_argument("--generations", type=int, default=10)
    parser.add_argument(
        "--research-demo", action="store_true",
        help="仅在规范输入缺失时使用草稿研究假设",
    )
    return parser.parse_args()


def summary_row(
    seed, backend, candidates, front, evaluation_budget, config,
    metadata=None, runtime_seconds=None,
):
    feasible = [item for item in candidates if item.feasible]
    return {
        "seed": seed,
        "backend": backend,
        "evaluation_budget": evaluation_budget,
        "candidate_count": len(candidates),
        "feasible_count": len(feasible),
        "feasible_ratio": len(feasible) / len(candidates) if candidates else 0.0,
        "pareto_count": len(front),
        "minimum_residential_disruption": min(
            item.objectives["residential_disruption"] for item in front
        ),
        "maximum_development_capacity": max(
            item.objectives["development_capacity"] for item in front
        ),
        "maximum_released_ground": max(
            item.objectives["street_connected_released_ground"] for item in front
        ),
        "unique_evaluations": (metadata or {}).get(
            "effective_independent_evaluations",
            (metadata or {}).get("effective_evaluation_budget", len(candidates) - 1),
        ),
        "runtime_seconds": runtime_seconds,
        **quality_summary(front, config),
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    args = parse_args()
    seeds = [int(value) for value in args.seeds.split(",")]
    if args.population < 2 or args.generations < 1 or not seeds:
        raise ValueError("population、generations 和 seeds 必须为正")
    evaluation_budget = args.population * args.generations
    study = load_study(
        args.scenario,
        research_demo=args.research_demo,
        shared_experiment_controls=True,
    )
    if study.blockers:
        raise RuntimeError(f"规范研究输入仍有阻塞项：{study.blockers}")
    specs = load_yaml(CONFIG_ROOT / "operator_specs.yaml").get("operators", {})
    rows = []
    comparisons = []
    convergence_rows = []
    for seed in seeds:
        started = time.perf_counter()
        nsga_candidates, nsga_front, nsga_metadata = run_nsga2(
            study, specs, population=args.population, generations=args.generations, seed=seed,
            evaluation_budget=evaluation_budget,
        )
        nsga_runtime = time.perf_counter() - started
        effective_budget = int(nsga_metadata["effective_evaluation_budget"])
        started = time.perf_counter()
        random_candidates, random_front, random_metadata = run_random_baseline(
            study, specs, samples=evaluation_budget, seed=seed, unique_samples=True
        )
        random_runtime = time.perf_counter() - started
        rows.append(summary_row(
            seed, "nsga2", nsga_candidates, nsga_front, effective_budget,
            study.objective_config, nsga_metadata, nsga_runtime
        ))
        rows.append(summary_row(
            seed, "random", random_candidates, random_front, effective_budget,
            study.objective_config, random_metadata, random_runtime,
        ))
        comparisons.append({
            "seed": seed,
            "nsga_dominates_random_fraction": coverage(nsga_front, random_front),
            "random_dominates_nsga_fraction": coverage(random_front, nsga_front),
            "nsga_pareto_count": len(nsga_front),
            "random_pareto_count": len(random_front),
            "effective_independent_evaluation_budget": effective_budget,
        })
        convergence_rows.extend(
            {"seed": seed, **row} for row in nsga_metadata.get("convergence", [])
        )
        print(
            f"seed={seed}: NSGA-II {len(nsga_front)} Pareto; "
            f"random {len(random_front)} Pareto; "
            f"C(NSGA,random)={comparisons[-1]['nsga_dominates_random_fraction']:.3f}"
        )

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = WS05 / "out" / "dapuqiao" / "experiments" / stamp
    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "search_summary.csv", rows)
    write_csv(output / "dominance_coverage.csv", comparisons)
    aggregate_rows = []
    for backend in ("nsga2", "random"):
        items = [row for row in rows if row["backend"] == backend]
        aggregate = {"backend": backend, "seed_count": len(items)}
        for key in (
            "feasible_ratio", "pareto_count", "hypervolume", "spacing",
            "runtime_seconds",
        ):
            values = [float(item[key]) for item in items]
            aggregate[f"{key}_mean"] = statistics.mean(values)
            aggregate[f"{key}_std"] = statistics.stdev(values) if len(values) > 1 else 0.0
        aggregate_rows.append(aggregate)
    write_csv(output / "aggregate_summary.csv", aggregate_rows)
    if convergence_rows:
        write_csv(output / "convergence.csv", convergence_rows)
    manifest = {
        "profile": "dapuqiao_v1",
        "scenario": args.scenario,
        "seeds": seeds,
        "population": args.population,
        "generations": args.generations,
        "equal_effective_independent_evaluation_budget": evaluation_budget,
        "common_hard_constraints": True,
        "normalization": study.objective_config.get("normalization_reference", {}),
        "hypervolume_reference": [1.1, 1.1, 1.1],
        "single_pass": True,
        "role_feedback_enabled": False,
        "input_mode": (
            "research_demo" if args.research_demo else "canonical_research_inputs"
        ),
        "research_demo": args.research_demo,
        "statutory_planning_result": False,
        "objective_interpretation": input_scope_metadata()["third_objective"],
        "documented_exclusions": {
            key: value for key, value in input_scope_metadata().items()
            if key != "third_objective"
        },
        "reproducibility": {
            "input_files": snapshot_inputs(output),
            "code_files": snapshot_code(output),
            "git": git_metadata(),
            "runtime": runtime_metadata(),
        },
        "interpretation": (
            "C(A,B) is the fraction of B's Pareto set strictly dominated by at least one "
            "solution from A. It measures search-result coverage without combining role weights."
        ),
    }
    (output / "experiment_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"输出：{output.relative_to(WS05)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

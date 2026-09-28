#!/usr/bin/env python3
"""Validate and freeze the planned high-budget Dapuqiao method comparison."""

from __future__ import annotations

import argparse
import inspect
import json
import sys
from datetime import datetime
from pathlib import Path


WS05 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WS05))

from engine.optimization.constraints import constraint_policy  # noqa: E402
from engine.optimization.data import CONFIG_ROOT, DATA_ROOT, load_study, load_yaml  # noqa: E402
from engine.optimization.objectives import evaluate_objectives  # noqa: E402
from engine.optimization.parameter_baseline import build_parameter_baseline_study  # noqa: E402
from run_dapuqiao_optimization import (  # noqa: E402
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
METHODS = ("conventional_parameter_baseline", *SCENARIOS)
EXPECTED_CONSTRAINT_CODES = {
    "geometry", "boundary", "heritage", "height_limit", "zone_far",
    "zone_coverage", "residential_retention", "new_overlap", "change_scope",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", default="11,23,37,53,71")
    parser.add_argument("--population", type=int, default=20)
    parser.add_argument("--generations", type=int, default=20)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def controls_signature(study) -> list[dict]:
    columns = ["zone_id", "height_limit_m", "max_far", "max_coverage_ratio"]
    return (
        study.controls[columns]
        .sort_values("zone_id")
        .round(9)
        .to_dict(orient="records")
    )


def main() -> int:
    args = parse_args()
    seeds = [int(value.strip()) for value in args.seeds.split(",") if value.strip()]
    if not seeds or args.population < 2 or args.generations < 1:
        raise ValueError("seeds、population 和 generations 必须为正")

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = (args.output or WS05 / "out" / "dapuqiao" / "formal_preflight" / stamp).resolve()
    output.mkdir(parents=True, exist_ok=True)
    checks: list[dict] = []

    def check(check_id: str, passed: bool, details) -> None:
        checks.append({"id": check_id, "passed": bool(passed), "details": details})

    studies = {
        scenario_id: load_study(
            scenario_id, research_demo=False, shared_experiment_controls=True
        )
        for scenario_id in SCENARIOS
    }
    blockers = {
        scenario_id: study.blockers
        for scenario_id, study in studies.items() if study.blockers
    }
    check("formal_inputs_have_no_blockers", not blockers, blockers or "none")

    signatures = {scenario_id: controls_signature(study) for scenario_id, study in studies.items()}
    first_signature = signatures[SCENARIOS[0]]
    check(
        "shared_planning_controls",
        all(signature == first_signature for signature in signatures.values()),
        {"zone_count": len(first_signature), "scenario_count": len(signatures)},
    )
    common_keys = (
        "height_limit_m", "max_far", "max_coverage_ratio",
        "minimum_residential_retention",
    )
    defaults = {
        scenario_id: {key: study.scenario["defaults"].get(key) for key in common_keys}
        for scenario_id, study in studies.items()
    }
    check(
        "shared_experiment_defaults",
        len({json.dumps(value, sort_keys=True) for value in defaults.values()}) == 1,
        defaults,
    )

    baseline_config = load_yaml(CONFIG_ROOT / "parameter_baseline.yaml")
    baseline_study = build_parameter_baseline_study(studies[SCENARIOS[0]], baseline_config)
    check(
        "parameter_baseline_constructs_from_shared_study",
        baseline_study.controls is not None and len(baseline_study.controls) == len(first_signature),
        {"control_rows": len(baseline_study.controls)},
    )

    spaces = studies[SCENARIOS[0]].public_space_candidates
    verification = studies[SCENARIOS[0]].public_space_verification
    summary = verification.get("summary", {})
    expected_public_summary = {
        "candidate_count": 2,
        "verified_public_park_context": 1,
        "unverified_excluded": 1,
        "included_in_objective": 0,
    }
    check("public_space_verification_summary", summary == expected_public_summary, summary)
    check(
        "public_space_rows_excluded_from_objective",
        "include_in_objective" in spaces.columns
        and spaces["include_in_objective"].fillna(False).eq(False).all(),
        spaces[["name", "research_status", "include_in_objective"]].to_dict(orient="records"),
    )
    alleys = studies[SCENARIOS[0]].alley_entrances
    alley_summary = studies[SCENARIOS[0]].alley_entrance_verification.get("summary", {})
    expected_alley_summary = {
        "candidate_count": 2,
        "verified_research_entrance": 1,
        "unverified_frozen": 1,
        "included_in_optimization": 0,
        "included_in_objective": 0,
        "exhaustive_inventory": False,
    }
    check("alley_entrance_verification_summary", alley_summary == expected_alley_summary, alley_summary)
    check(
        "alley_entrance_rows_frozen_from_optimization",
        len(alleys) == 2
        and alleys["include_in_optimization"].fillna(False).eq(False).all()
        and alleys["include_in_objective"].fillna(False).eq(False).all(),
        alleys[["name", "research_status", "include_in_optimization"]].to_dict(orient="records"),
    )

    objective_config = load_yaml(CONFIG_ROOT / "objectives.yaml")
    dependency = objective_config.get("data_dependencies", {}).get(
        "street_connected_released_ground", {}
    )
    required = set(dependency.get("required_layers", []))
    excluded = set(dependency.get("excluded_context_layers", []))
    objective_parameters = set(inspect.signature(evaluate_objectives).parameters)
    objective_scope_ok = (
        required == {"buildings.parquet", "street_network.geojson", "study_boundary.geojson"}
        and excluded == {
            "public_space_candidates.geojson", "public_space_verification.json",
            "alley_entrances.geojson", "alley_entrance_verification.json",
        }
        and not any(
            token in name for name in objective_parameters
            for token in ("public_space", "alley", "entrance")
        )
    )
    check(
        "third_objective_dependency_scope",
        objective_scope_ok,
        {
            "required_layers": sorted(required),
            "excluded_context_layers": sorted(excluded),
            "function_parameters": sorted(objective_parameters),
        },
    )

    input_scope = input_scope_metadata()
    check(
        "heritage_and_unmatched_counts_are_separate",
        input_scope["heritage_records_unresolved_and_excluded"] == 4
        and input_scope["buildings_unmatched_to_zones_and_frozen"] == 32,
        {
            "heritage_records_unresolved_and_excluded": input_scope[
                "heritage_records_unresolved_and_excluded"
            ],
            "buildings_unmatched_to_zones_and_frozen": input_scope[
                "buildings_unmatched_to_zones_and_frozen"
            ],
        },
    )

    policy = constraint_policy()
    rules = {str(rule.get("violation_code")): rule for rule in policy.values()}
    check(
        "constraint_rules_complete_and_blocking",
        set(rules) == EXPECTED_CONSTRAINT_CODES
        and all(rule.get("severity") == "blocking" for rule in rules.values())
        and all(rule.get("handling") == "reject_candidate" for rule in rules.values()),
        {
            code: {
                "severity": rule.get("severity"),
                "handling": rule.get("handling"),
                "prevention": rule.get("prevention"),
            }
            for code, rule in sorted(rules.items())
        },
    )

    evaluation_budget = args.population * args.generations
    run_count = len(METHODS) * len(seeds)
    ready = all(item["passed"] for item in checks)
    command = (
        "python scripts/compare_dapuqiao_methods.py "
        f"--seeds {','.join(map(str, seeds))} --population {args.population} "
        f"--generations {args.generations}"
    )
    manifest = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "ready": ready,
        "checks": checks,
        "plan": {
            "methods": list(METHODS),
            "seeds": seeds,
            "population": args.population,
            "generations": args.generations,
            "effective_independent_evaluations_per_run": evaluation_budget,
            "run_count": run_count,
            "total_effective_independent_evaluations": evaluation_budget * run_count,
            "geometry_exports_required": True,
            "recommended_command": command,
        },
        "input_scope": input_scope,
        "reproducibility": {
            "input_files": snapshot_inputs(output),
            "code_files": snapshot_code(output),
            "git": git_metadata(),
            "runtime": runtime_metadata(),
        },
        "notes": [
            "Preflight performs no optimization evaluations.",
            "A dirty working tree is recorded, not treated as a blocker, because exact inputs and code are snapshotted.",
            "No runtime estimate is inferred.",
        ],
    }
    manifest_path = output / "preflight_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "ready": ready,
        "manifest": str(manifest_path),
        "run_count": run_count,
        "total_effective_independent_evaluations": evaluation_budget * run_count,
        "recommended_command": command,
    }, ensure_ascii=False, indent=2))
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())

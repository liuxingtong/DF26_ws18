#!/usr/bin/env python3
"""Audit or run the single-pass Dapuqiao morphology optimization framework.

The default backend is NSGA-II; a reproducible random backend is retained for
algorithm comparison. ``--research-demo`` is only a disclosed draft-input
fallback and must never be presented as a statutory planning result.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
from importlib import metadata as package_metadata
import json
import platform
import shutil
import subprocess
import sys
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path


WS05 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WS05))

from engine.optimization.data import (  # noqa: E402
    CONFIG_ROOT,
    DATA_ROOT,
    audit_dict,
    load_study,
    load_yaml,
)
from engine.optimization.metrics import (  # noqa: E402
    epsilon_sensitivity,
    front_distribution,
    quality_summary,
)
from engine.optimization.roles import (  # noqa: E402
    evaluate_role_priority_sensitivity,
    evaluate_roles,
)
from engine.optimization.search import run_random_baseline  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    audit = sub.add_parser("audit", help="检查数据是否足以进行正式优化")
    audit.add_argument("--research-demo", action="store_true", help="同时显示调试假设后的状态")

    run = sub.add_parser("run", help="运行可复现随机搜索基线和角色后评价")
    run.add_argument("--scenario", default="public_coordination")
    run.add_argument("--samples", type=int, default=100)
    run.add_argument("--backend", choices=["random", "nsga2"], default="nsga2")
    run.add_argument("--population", type=int, default=40)
    run.add_argument("--generations", type=int, default=20)
    run.add_argument("--seed", type=int, default=42)
    run.add_argument("--research-demo", action="store_true",
                     help="使用明确披露的研究假设输入；结果不得解释为法定规划")
    return parser.parse_args()


def candidate_row(candidate) -> dict:
    def active(item) -> bool:
        return getattr(item, "operator", "parameter") != "noop"

    def signature(item) -> str:
        if hasattr(item, "height_multiplier"):
            return (
                f"{item.zone_id}:parameter:height_multiplier={item.height_multiplier:.4f},"
                f"footprint_ratio={item.footprint_ratio:.4f}"
            )
        return f"{item.zone_id}:{item.operator}:{item.intensity:.4f}"

    row = {
        "solution_id": candidate.solution_id,
        "feasible": candidate.feasible,
        "violation_count": len(candidate.violations),
        "changed_zone_count": len({item.zone_id for item in candidate.decisions if active(item)}),
        "decision_signature": ";".join(
            signature(item)
            for item in candidate.decisions if active(item)
        ),
    }
    row.update(candidate.objectives)
    row.update(candidate.descriptors)
    return row


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


INPUT_FILES = (
    "SOURCE_ARCHIVE.json",
    "buildings.parquet",
    "study_boundary.geojson",
    "street_network.geojson",
    "public_services.geojson",
    "public_space_candidates.geojson",
    "public_space_verification.json",
    "alley_entrances.geojson",
    "alley_entrance_verification.json",
    "online_gap_freeze.json",
    "open_data_quality.json",
    "open_data_sources.yaml",
    "intervention_zones.geojson",
    "planning_controls.csv",
    "heritage_buildings.geojson",
    "formal_input_quality.json",
    "site.yaml",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_metadata() -> dict:
    def run(*args: str) -> str | None:
        try:
            result = subprocess.run(
                ["git", *args], cwd=WS05, check=True, capture_output=True, text=True
            )
        except (OSError, subprocess.CalledProcessError):
            return None
        return result.stdout.strip()

    status = run("status", "--porcelain")
    return {
        "commit": run("rev-parse", "HEAD"),
        "branch": run("branch", "--show-current"),
        "working_tree_dirty": bool(status) if status is not None else None,
    }


def snapshot_inputs(output: Path) -> dict[str, dict[str, str | int]]:
    snapshot = output / "inputs"
    snapshot.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for name in INPUT_FILES:
        source = DATA_ROOT / name
        if not source.exists():
            continue
        shutil.copy2(source, snapshot / name)
        manifest[name] = {
            "sha256": sha256(source),
            "bytes": source.stat().st_size,
        }
    return manifest


def snapshot_code(output: Path) -> dict[str, dict[str, str | int]]:
    """Copy the exact optimization code used, including dirty/untracked files."""
    sources = [
        *sorted((WS05 / "engine" / "optimization").glob("*.py")),
        *sorted((WS05 / "scripts").glob("*dapuqiao*.py")),
        *sorted(CONFIG_ROOT.glob("*.yaml")),
        WS05 / "engine" / "requirements.txt",
    ]
    snapshot = output / "code"
    manifest = {}
    for source in sources:
        if not source.exists():
            continue
        relative = source.relative_to(WS05)
        destination = snapshot / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        manifest[str(relative)] = {
            "sha256": sha256(source),
            "bytes": source.stat().st_size,
        }
    return manifest


def runtime_metadata() -> dict:
    packages = {}
    for name in ("geopandas", "pandas", "shapely", "numpy", "pymoo", "pyarrow", "PyYAML"):
        try:
            packages[name] = package_metadata.version(name)
        except package_metadata.PackageNotFoundError:
            packages[name] = None
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "packages": packages,
    }


def input_scope_metadata() -> dict:
    quality_path = DATA_ROOT / "formal_input_quality.json"
    verification_path = DATA_ROOT / "public_space_verification.json"
    alley_verification_path = DATA_ROOT / "alley_entrance_verification.json"
    freeze_path = DATA_ROOT / "online_gap_freeze.json"
    quality = (
        json.loads(quality_path.read_text(encoding="utf-8"))
        if quality_path.exists() else {}
    )
    verification = (
        json.loads(verification_path.read_text(encoding="utf-8"))
        if verification_path.exists() else {}
    )
    alley_verification = (
        json.loads(alley_verification_path.read_text(encoding="utf-8"))
        if alley_verification_path.exists() else {}
    )
    freeze_register = (
        json.loads(freeze_path.read_text(encoding="utf-8"))
        if freeze_path.exists() else {}
    )
    objective_config = load_yaml(CONFIG_ROOT / "objectives.yaml")
    dependency = objective_config.get("data_dependencies", {}).get(
        "street_connected_released_ground", {}
    )
    buffer_m = float(
        objective_config.get("measurement", {}).get("street_access_buffer_m", 5.0)
    )
    counts = quality.get("counts", {})
    return {
        "heritage_records_unresolved_and_excluded": int(
            counts.get("heritage_official_records_unresolved_and_excluded", 0)
        ),
        "buildings_unmatched_to_zones_and_frozen": int(
            counts.get("buildings_unmatched_and_frozen", 0)
        ),
        "public_space_context": verification.get("summary", {}),
        "alley_entrance_context": alley_verification.get("summary", {}),
        "online_gap_freeze": freeze_register.get("summary", {}),
        "third_objective": {
            "id": "street_connected_released_ground",
            "interpretation": "street-connected released-ground potential",
            "required_layers": dependency.get("required_layers", []),
            "excluded_context_layers": dependency.get("excluded_context_layers", []),
            "street_access_buffer_m": buffer_m,
            "public_space_candidates_used": False,
            "not_interpreted_as": [
                "public-space area", "public-space ownership", "public-space accessibility",
                "historical park area", "OSM research polygon", "alley entrance point",
            ],
        },
    }


def export_run(study, candidates, pareto, role_rows, selections, *, seed: int, samples: int,
               search_metadata: dict, output_dir: Path | None = None,
               method_id: str | None = None, export_geometries: bool = True,
               role_priority_sensitivity_rows: list[dict] | None = None,
               quality_config: dict | None = None,
               optimization_runtime_seconds: float | None = None) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    scenario_id = study.scenario.get("id", "scenario")
    output = output_dir or (
        WS05 / "out" / "dapuqiao" / "optimization" / f"{scenario_id}__{stamp}"
    )
    (output / "solutions").mkdir(parents=True, exist_ok=True)
    (output / "provenance").mkdir(parents=True, exist_ok=True)
    (output / "config").mkdir(parents=True, exist_ok=True)
    input_manifest = snapshot_inputs(output)

    quality_config = quality_config or study.objective_config
    run_config = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "seed": seed,
        "samples": samples if search_metadata.get("backend") == "random" else None,
        "scenario_id": scenario_id,
        "method_id": method_id or scenario_id,
        "scenario": study.scenario.get("label"),
        "source_status": study.source_status,
        "warnings": study.warnings,
        "single_pass": True,
        "role_feedback_enabled": False,
        "role_preference_model": {
            "type": "epsilon_tiered_lexicographic",
            "compromise": "minimum_worst_role_rank",
            "numeric_weights_used": False,
        },
        "objective_measurement": study.objective_config.get("measurement", {}),
        "epsilon": study.objective_config.get("epsilon", {}),
        "exported_epsilon_pareto_solution_count": len(pareto),
        "quality_normalization_reference": quality_config.get(
            "normalization_reference", {}
        ),
        "quality": quality_summary(pareto, quality_config),
        "search": search_metadata,
        "reproducibility": {
            "input_files": input_manifest,
            "code_files": snapshot_code(output),
            "git": git_metadata(),
            "runtime": runtime_metadata(),
            "optimization_runtime_seconds": optimization_runtime_seconds,
        },
        "input_scope": input_scope_metadata(),
    }
    (output / "run_config.json").write_text(
        json.dumps(run_config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    write_csv(output / "all_candidates.csv", [candidate_row(item) for item in candidates])
    write_csv(output / "pareto_solutions.csv", [candidate_row(item) for item in pareto])
    by_id = {candidate.solution_id: candidate for candidate in candidates}
    full_pareto = [
        by_id[solution_id]
        for solution_id in search_metadata.get("full_pareto_solution_ids", [])
        if solution_id in by_id
    ]
    representatives = [
        by_id[solution_id]
        for solution_id in search_metadata.get("representative_solution_ids", [])
        if solution_id in by_id
    ]
    write_csv(output / "pareto_full.csv", [candidate_row(item) for item in full_pareto])
    write_csv(
        output / "representative_solutions.csv",
        [candidate_row(item) for item in representatives],
    )
    write_csv(
        output / "pareto_distribution.csv",
        [
            *front_distribution(full_pareto, "exact_full"),
            *front_distribution(pareto, "epsilon_filtered"),
            *front_distribution(representatives, "representative"),
        ],
    )
    write_csv(output / "role_rankings.csv", role_rows)
    write_csv(
        output / "role_priority_sensitivity.csv",
        role_priority_sensitivity_rows or [],
    )
    write_csv(
        output / "epsilon_sensitivity.csv",
        epsilon_sensitivity(candidates, study.objective_config),
    )
    write_csv(output / "convergence.csv", search_metadata.get("convergence", []))
    violation_rows = []
    for candidate in candidates:
        for item in candidate.violations:
            violation_rows.append({"solution_id": candidate.solution_id, **asdict(item)})
    write_csv(output / "constraint_violations.csv", violation_rows)
    (output / "selected_solutions.json").write_text(
        json.dumps(selections, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # Export every Pareto geometry so each point in the interface can open its
    # corresponding 3D scheme. Role labels remain aliases on the same file.
    labels_by_solution = {candidate.solution_id: ["pareto"] for candidate in pareto}
    for candidate in representatives:
        labels_by_solution.setdefault(candidate.solution_id, []).append("representative")
    selected_ids = {"current": candidates[0].solution_id, **selections}
    for label, solution_id in selected_ids.items():
        labels = labels_by_solution.setdefault(solution_id, [])
        if label not in labels:
            labels.append(label)
    for solution_id, labels in labels_by_solution.items():
        candidate = by_id[solution_id]
        label = "__".join(labels)
        if export_geometries:
            geojson = candidate.buildings.to_json(drop_id=True, ensure_ascii=False)
            (output / "solutions" / f"{label}__{solution_id}.geojson").write_text(geojson, encoding="utf-8")
        provenance = {
            "labels": labels,
            "solution_id": solution_id,
            "objectives": candidate.objectives,
            "descriptors": candidate.descriptors,
            "decisions": [asdict(item) for item in candidate.decisions],
            "changes": candidate.changes,
            "violations": [asdict(item) for item in candidate.violations],
        }
        (output / "provenance" / f"{label}__{solution_id}.json").write_text(
            json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    for config_path in CONFIG_ROOT.glob("*.yaml"):
        shutil.copy2(config_path, output / "config" / config_path.name)
    return output


def main() -> int:
    args = parse_args()
    scenario_name = getattr(args, "scenario", "public_coordination")
    study = load_study(scenario_name, research_demo=args.research_demo)
    if args.command == "audit":
        print(json.dumps(audit_dict(study), ensure_ascii=False, indent=2))
        return 0 if not study.blockers else 2

    if study.blockers:
        print("正式运行尚未开始：", file=sys.stderr)
        for blocker in study.blockers:
            print(f"- {blocker}", file=sys.stderr)
        print("可先使用 audit；如仅调试代码，显式加 --research-demo。", file=sys.stderr)
        return 2

    operator_specs = load_yaml(CONFIG_ROOT / "operator_specs.yaml").get("operators", {})
    role_config = load_yaml(CONFIG_ROOT / "role_profiles.yaml")
    started = time.perf_counter()
    if args.backend == "nsga2":
        from engine.optimization.nsga2 import run_nsga2

        candidates, pareto, search_metadata = run_nsga2(
            study,
            operator_specs,
            population=args.population,
            generations=args.generations,
            seed=args.seed,
        )
    else:
        candidates, pareto, search_metadata = run_random_baseline(
            study, operator_specs, samples=args.samples, seed=args.seed
        )
    epsilon = study.objective_config.get("epsilon", {})
    role_rows, selections = evaluate_roles(pareto, role_config, epsilon)
    role_priority_sensitivity_rows = evaluate_role_priority_sensitivity(
        pareto, role_config, epsilon
    )
    optimization_runtime_seconds = time.perf_counter() - started
    output = export_run(
        study, candidates, pareto, role_rows, selections, seed=args.seed, samples=args.samples,
        search_metadata=search_metadata,
        role_priority_sensitivity_rows=role_priority_sensitivity_rows,
        optimization_runtime_seconds=optimization_runtime_seconds,
    )
    print(f"候选方案：{len(candidates)}")
    print(f"可行方案：{sum(item.feasible for item in candidates)}")
    print(f"帕累托方案：{len(pareto)}")
    print(f"输出：{output.relative_to(WS05)}")
    if args.research_demo:
        print("注意：这是研究假设实验结果，不是法定规划结果；论文中必须披露输入假设。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Sweep every zone/operator/intensity under the frozen Dapuqiao inputs."""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

import pandas as pd


WS05 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WS05))

from engine.optimization.data import CONFIG_ROOT, load_study, load_yaml  # noqa: E402
from engine.optimization.models import ZoneDecision  # noqa: E402
from engine.optimization.objectives import build_objective_context  # noqa: E402
from engine.optimization.search import evaluate_candidate  # noqa: E402
from run_dapuqiao_optimization import (  # noqa: E402
    git_metadata,
    input_scope_metadata,
    runtime_metadata,
    snapshot_code,
    snapshot_inputs,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", default="dapuqiao_tourism_livability")
    parser.add_argument("--intensities", default="0.25,0.50,0.75,1.00")
    parser.add_argument(
        "--research-demo", action="store_true",
        help="仅在规范输入缺失时使用草稿研究假设",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    started = time.perf_counter()
    intensities = [float(value) for value in args.intensities.split(",")]
    if not intensities or any(value <= 0 or value > 1 for value in intensities):
        raise ValueError("强度必须位于 (0, 1]")

    study = load_study(args.scenario, research_demo=args.research_demo)
    if study.blockers:
        raise RuntimeError(f"规范研究输入仍有阻塞项：{study.blockers}")
    specs = load_yaml(CONFIG_ROOT / "operator_specs.yaml").get("operators", {})
    zone_ids = sorted(study.zones["zone_id"].astype(str).unique())
    context = build_objective_context(
        study.buildings, study.boundary, study.streets, study.scenario
    )
    base_gfa = float(
        (study.buildings.geometry.area * study.buildings["height_m"] / 3.5).sum()
    )
    rows = []
    for zone_id in zone_ids:
        zone_buildings = study.buildings[study.buildings["zone_id"].astype(str).eq(zone_id)]
        eligible_count = int(
            (zone_buildings["editable"].fillna(False)
             & ~zone_buildings["heritage"].fillna(False)).sum()
        )
        for operator in ("densify", "open_ground"):
            for intensity in intensities:
                decisions = [
                    ZoneDecision(item, operator if item == zone_id else "noop",
                                 intensity if item == zone_id else 0.0)
                    for item in zone_ids
                ]
                candidate = evaluate_candidate(
                    study, decisions, specs,
                    f"CAL_{zone_id}_{operator}_{intensity:.2f}", context,
                )
                candidate_gfa = float(
                    (candidate.buildings.geometry.area
                     * candidate.buildings["height_m"] / 3.5).sum()
                )
                allocations = [
                    item["capacity_allocation_ratio"] for item in candidate.changes
                    if item["operator"] == "densify"
                ]
                no_change_reason = ""
                if not candidate.changes:
                    if eligible_count == 0:
                        no_change_reason = "no_editable_nonheritage_buildings"
                    elif operator == "densify":
                        no_change_reason = "no_far_or_height_headroom"
                    else:
                        no_change_reason = "operator_produced_no_geometry_change"
                rows.append({
                    "zone_id": zone_id,
                    "operator": operator,
                    "requested_intensity": intensity,
                    "zone_buildings": int(len(zone_buildings)),
                    "eligible_buildings": eligible_count,
                    "changed_buildings": len(candidate.changes),
                    "feasible": candidate.feasible,
                    "violations": ";".join(sorted({item.code for item in candidate.violations})),
                    "no_change_reason": no_change_reason,
                    "capacity_allocation_ratio": min(allocations) if allocations else None,
                    "gfa_delta_m2": candidate_gfa - base_gfa,
                    **candidate.objectives,
                    **candidate.descriptors,
                })

    output = WS05 / "out" / "dapuqiao" / "calibration"
    output.mkdir(parents=True, exist_ok=True)
    input_manifest = snapshot_inputs(output)
    table = pd.DataFrame(rows)
    table.to_csv(output / "operator_calibration.csv", index=False, encoding="utf-8-sig")
    violations = Counter(
        code for value in table["violations"] if value
        for code in value.split(";") if code
    )
    summary = {
        "profile": "dapuqiao_v1",
        "input_mode": (
            "research_demo" if args.research_demo else "canonical_research_inputs"
        ),
        "zones": len(zone_ids),
        "intensities": intensities,
        "evaluations": len(table),
        "feasible_evaluations": int(table["feasible"].sum()),
        "no_change_evaluations": int(table["changed_buildings"].eq(0).sum()),
        "violation_counts": dict(violations),
        "zones_without_densify_effect": sorted(table[
            table["operator"].eq("densify") & table["changed_buildings"].eq(0)
        ]["zone_id"].unique()),
        "zones_without_open_ground_effect": sorted(table[
            table["operator"].eq("open_ground") & table["changed_buildings"].eq(0)
        ]["zone_id"].unique()),
        "maximum_gfa_delta_m2": float(table["gfa_delta_m2"].max()),
        "maximum_released_ground_ratio": float(
            table["street_connected_released_ground"].max()
        ),
        "input_scope": input_scope_metadata(),
        "reproducibility": {
            "input_files": input_manifest,
            "code_files": snapshot_code(output),
            "git": git_metadata(),
            "runtime": runtime_metadata(),
            "runtime_seconds": time.perf_counter() - started,
        },
    }
    (output / "operator_calibration_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"输出：{output.relative_to(WS05)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

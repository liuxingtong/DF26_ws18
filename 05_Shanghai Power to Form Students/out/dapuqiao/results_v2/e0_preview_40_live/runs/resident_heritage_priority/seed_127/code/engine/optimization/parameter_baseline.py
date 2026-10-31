from __future__ import annotations

import math
from copy import deepcopy
from dataclasses import replace
from typing import Any

import numpy as np
import pandas as pd
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import ElementwiseProblem
from pymoo.optimize import minimize
from shapely import affinity

from .constraints import check_constraints
from .models import CandidateEvaluation, ParameterDecision
from .metrics import quality_summary
from .nsga2 import ConvergenceRecorder
from .objectives import build_objective_context, evaluate_objectives
from .pareto import morphology_signature, pareto_sets


FLOOR_HEIGHT_M = 3.5


def build_parameter_baseline_study(study, baseline_config: dict[str, Any]):
    """Reuse study data and shared controls while removing governance permissions."""
    config = baseline_config.get("baseline", baseline_config)
    scenario = {
        "id": config["id"],
        "label": config["label"],
        "description": config.get("description", ""),
        "source_status": config.get("source_status", "research_assumption"),
        "defaults": deepcopy(study.scenario.get("defaults", {})),
        "implementation": deepcopy(config.get("implementation", {})),
        "parameter_ranges": deepcopy(config.get("parameters", {})),
        "method": "conventional_parameter_baseline",
    }
    status = dict(study.source_status)
    status["generation_logic"] = "geometry_parameters_without_stakeholder_permissions"
    return replace(study, scenario=scenario, source_status=status)


def _parameter_ranges(config: dict[str, Any]) -> tuple[float, float, float, float]:
    config = config.get("baseline", config)
    parameters = config.get("parameters", {})
    height = parameters.get("height_multiplier", {})
    footprint = parameters.get("footprint_ratio", {})
    return (
        float(height.get("min", 1.0)),
        float(height.get("max", 1.30)),
        float(footprint.get("min", 0.75)),
        float(footprint.get("max", 1.0)),
    )


def _eligible_mask(rows):
    # Deliberately ignore stakeholder_proxy and editable: the latter is derived
    # from stakeholder==state in the teaching data. Heritage remains a shared
    # hard constraint and unmatched buildings never enter a zone.
    return ~rows["heritage"].fillna(False)


def _impact_counts(study) -> dict[str, int]:
    counts = {}
    for zone_id in study.zones["zone_id"].astype(str):
        rows = study.buildings[study.buildings["zone_id"].astype(str).eq(zone_id)]
        counts[zone_id] = int(_eligible_mask(rows).sum())
    return counts


def _decode_vector(
    vector,
    zone_ids: list[str],
    ranges: tuple[float, float, float, float],
    maximum_changed_zone_ratio: float,
    impact_counts: dict[str, int],
    maximum_changed_buildings: int,
) -> list[ParameterDecision]:
    h_min, h_max, f_min, f_max = ranges
    proposals = []
    for index, zone_id in enumerate(zone_ids):
        height_multiplier = float(np.clip(vector[index * 2], h_min, h_max))
        footprint_ratio = float(np.clip(vector[index * 2 + 1], f_min, f_max))
        h_span = max(h_max - h_min, 1e-12)
        f_span = max(f_max - f_min, 1e-12)
        magnitude = (
            (height_multiplier - h_min) / h_span
            + (f_max - footprint_ratio) / f_span
        )
        proposals.append((magnitude, ParameterDecision(
            zone_id=zone_id,
            height_multiplier=height_multiplier,
            footprint_ratio=footprint_ratio,
        )))

    maximum_changed_zones = max(1, round(len(zone_ids) * maximum_changed_zone_ratio))
    selected = []
    used_buildings = 0
    for _, decision in sorted(proposals, key=lambda item: item[0], reverse=True):
        impact = impact_counts.get(decision.zone_id, 0)
        if impact <= 0 or used_buildings + impact > maximum_changed_buildings:
            continue
        selected.append(decision)
        used_buildings += impact
        if len(selected) >= maximum_changed_zones:
            break
    return sorted(selected, key=lambda item: zone_ids.index(item.zone_id))


def _decision_key(decisions: list[ParameterDecision]) -> tuple:
    return tuple(
        (item.zone_id, round(item.height_multiplier, 6), round(item.footprint_ratio, 6))
        for item in decisions
    )


def apply_parameter_decisions(study, decisions: list[ParameterDecision]):
    result = study.buildings.copy(deep=True)
    result["applied_operator"] = "noop"
    result["operator_intensity"] = 0.0
    controls = {
        str(row["zone_id"]): row.to_dict()
        for _, row in study.controls.iterrows()
    } if study.controls is not None else {}
    zone_areas = {
        str(row["zone_id"]): float(row.geometry.area)
        for _, row in study.zones.iterrows()
    }
    changes = []
    numerical = getattr(study, "objective_config", {}).get("numerical_resolution", {})
    minimum_gfa_change = float(numerical.get("minimum_building_gfa_change_m2", 1.0))
    minimum_footprint_change = float(
        numerical.get("minimum_building_footprint_change_m2", 1.0)
    )
    minimum_height_change = float(numerical.get("minimum_building_height_change_m", 0.1))

    for decision in decisions:
        zone_id = str(decision.zone_id)
        zone_mask = result["zone_id"].astype(str).eq(zone_id)
        eligible = zone_mask & _eligible_mask(result)
        indices = list(result.index[eligible])
        if not indices:
            continue
        control = controls.get(zone_id, {})
        height_limit = pd.to_numeric(control.get("height_limit_m"), errors="coerce")
        max_far = pd.to_numeric(control.get("max_far"), errors="coerce")
        zone_area = zone_areas.get(zone_id, 0.0)

        target_geometries = {}
        target_heights = {}
        base_height_gfa = 0.0
        requested_extra_gfa = 0.0
        for index in indices:
            before_geometry = result.at[index, "geometry"]
            scale = math.sqrt(max(decision.footprint_ratio, 1e-9))
            scaled = affinity.scale(before_geometry, xfact=scale, yfact=scale, origin="centroid")
            clipped = scaled.intersection(before_geometry)
            after_geometry = clipped if not clipped.is_empty and clipped.area > 1e-6 else before_geometry
            before_height = float(result.at[index, "height_m"])
            allowed_height = max(before_height, float(height_limit)) if pd.notna(height_limit) else math.inf
            target_height = min(before_height * decision.height_multiplier, allowed_height)
            target_geometries[index] = after_geometry
            target_heights[index] = target_height
            base_height_gfa += float(after_geometry.area) * before_height / FLOOR_HEIGHT_M
            requested_extra_gfa += (
                float(after_geometry.area) * max(target_height - before_height, 0.0) / FLOOR_HEIGHT_M
            )

        ineligible = result[zone_mask & ~eligible]
        fixed_gfa = float((ineligible.geometry.area * ineligible["height_m"] / FLOOR_HEIGHT_M).sum())
        baseline_zone = study.buildings[study.buildings["zone_id"].astype(str).eq(zone_id)]
        baseline_gfa = float(
            (baseline_zone.geometry.area * baseline_zone["height_m"] / FLOOR_HEIGHT_M).sum()
        )
        baseline_far = baseline_gfa / zone_area if zone_area > 0 else 0.0
        allowed_far = max(float(max_far), baseline_far) if pd.notna(max_far) else math.inf
        allowed_gfa = allowed_far * zone_area if math.isfinite(allowed_far) else math.inf
        available_extra_gfa = max(allowed_gfa - fixed_gfa - base_height_gfa, 0.0)
        height_allocation = (
            min(1.0, available_extra_gfa / requested_extra_gfa)
            if requested_extra_gfa > 0 else 1.0
        )

        for index in indices:
            before_geometry = result.at[index, "geometry"]
            before_height = float(result.at[index, "height_m"])
            after_geometry = target_geometries[index]
            requested_height = target_heights[index]
            after_height = before_height + (requested_height - before_height) * height_allocation
            footprint_change_m2 = abs(float(after_geometry.area - before_geometry.area))
            height_change_m = abs(after_height - before_height)
            before_gfa_m2 = float(before_geometry.area) * before_height / FLOOR_HEIGHT_M
            after_gfa_m2 = float(after_geometry.area) * after_height / FLOOR_HEIGHT_M
            gfa_change_m2 = abs(after_gfa_m2 - before_gfa_m2)
            if not (
                footprint_change_m2 >= minimum_footprint_change
                or height_change_m >= minimum_height_change
                or gfa_change_m2 >= minimum_gfa_change
            ):
                continue
            result.at[index, "geometry"] = after_geometry
            result.at[index, "height_m"] = after_height
            result.at[index, "applied_operator"] = "parameter_height_footprint"
            result.at[index, "operator_intensity"] = decision.intensity
            changes.append({
                "bid": str(result.at[index, "bid"]),
                "zone_id": zone_id,
                "operator": "parameter_height_footprint",
                "intensity": decision.intensity,
                "height_multiplier": decision.height_multiplier,
                "footprint_ratio": decision.footprint_ratio,
                "before_height_m": before_height,
                "after_height_m": after_height,
                "before_area_m2": float(before_geometry.area),
                "after_area_m2": float(after_geometry.area),
                "footprint_change_m2": footprint_change_m2,
                "gfa_change_m2": float(after_gfa_m2 - before_gfa_m2),
                "requested_height_m": requested_height,
                "capacity_allocation_ratio": height_allocation,
            })
    return result, changes


def evaluate_parameter_candidate(study, decisions, solution_id: str, objective_context=None):
    candidate, changes = apply_parameter_decisions(study, decisions)
    violations = check_constraints(
        study.buildings, candidate, study.boundary, study.zones, study.controls, study.scenario
    )
    objectives, descriptors = evaluate_objectives(
        study.buildings, candidate, changes, study.boundary, study.streets, study.scenario,
        context=objective_context, objective_config=getattr(study, "objective_config", {}),
    )
    return CandidateEvaluation(
        solution_id=solution_id,
        decisions=decisions,
        buildings=candidate,
        changes=changes,
        objectives=objectives,
        descriptors=descriptors,
        violations=violations,
    )


class ParameterBaselineProblem(ElementwiseProblem):
    def __init__(self, study, baseline_config: dict[str, Any]):
        self.study = study
        self.config = baseline_config.get("baseline", baseline_config)
        self.zone_ids = sorted(study.zones["zone_id"].astype(str).unique())
        self.ranges = _parameter_ranges(baseline_config)
        implementation = self.config.get("implementation", {})
        self.maximum_changed_zone_ratio = float(
            implementation.get("maximum_changed_zone_ratio", 0.40)
        )
        self.maximum_changed_buildings = math.floor(
            len(study.buildings) * float(implementation.get("maximum_changed_building_ratio", 0.30))
        )
        self.impact_counts = _impact_counts(study)
        self.objective_context = build_objective_context(
            study.buildings, study.boundary, study.streets, study.scenario,
            getattr(study, "objective_config", {}),
        )
        self.cache = {}
        self.evaluations = []
        self.evaluation_calls = 0
        h_min, h_max, f_min, f_max = self.ranges
        lower = np.tile([h_min, f_min], len(self.zone_ids))
        upper = np.tile([h_max, f_max], len(self.zone_ids))
        super().__init__(n_var=len(self.zone_ids) * 2, n_obj=3, n_ieq_constr=1, xl=lower, xu=upper)

    def _evaluate(self, vector, out, *args, **kwargs):
        self.evaluation_calls += 1
        decisions = _decode_vector(
            vector,
            self.zone_ids,
            self.ranges,
            self.maximum_changed_zone_ratio,
            self.impact_counts,
            self.maximum_changed_buildings,
        )
        key = _decision_key(decisions)
        candidate = self.cache.get(key)
        if candidate is None:
            candidate = evaluate_parameter_candidate(
                self.study,
                decisions,
                f"P_{len(self.evaluations) + 1:05d}",
                self.objective_context,
            )
            self.cache[key] = candidate
            self.evaluations.append(candidate)
        out["F"] = np.asarray(candidate.minimization_vector(), dtype=float)
        out["G"] = np.asarray([
            sum(item.severity == "blocking" for item in candidate.violations)
        ], dtype=float)


def run_parameter_baseline(
    study,
    baseline_config: dict[str, Any],
    *,
    population: int = 40,
    generations: int = 20,
    seed: int = 42,
    evaluation_budget: int | None = None,
):
    if study.blockers:
        raise RuntimeError("正式运行被数据审计阻止：" + "；".join(study.blockers))
    target_budget = evaluation_budget or population * generations
    attempted_generations = generations
    while True:
        problem = ParameterBaselineProblem(study, baseline_config)
        algorithm = NSGA2(pop_size=population, eliminate_duplicates=True)
        recorder = ConvergenceRecorder(getattr(study, "objective_config", {}))
        minimize(
            problem,
            algorithm,
            termination=("n_gen", attempted_generations),
            seed=seed,
            verbose=False,
            save_history=False,
            callback=recorder,
        )
        active_by_morphology = {}
        for candidate in problem.evaluations:
            if candidate.has_effective_change:
                active_by_morphology.setdefault(morphology_signature(candidate), candidate)
        active = list(active_by_morphology.values())
        if len(active) >= target_budget:
            break
        if attempted_generations >= max(generations * 20, generations + 200):
            raise RuntimeError(
                f"参数基线只能生成 {len(active)} 个独立非空候选，未达到预算 {target_budget}"
            )
        observed = max(len(active), 1)
        attempted_generations = max(
            attempted_generations + 1,
            math.ceil(attempted_generations * target_budget / observed * 1.05),
        )

    baseline = evaluate_parameter_candidate(
        study,
        [],
        "P_00000",
        problem.objective_context,
    )
    candidates = [baseline, *active[:target_budget]]
    full_front, epsilon_front, representatives, diagnostics = pareto_sets(
        candidates, getattr(study, "objective_config", {})
    )
    convergence = [
        row for row in recorder.records
        if int(row["effective_independent_evaluations"]) < target_budget
    ]
    boundary_record = next(
        (
            row for row in recorder.records
            if int(row["effective_independent_evaluations"]) >= target_budget
        ),
        None,
    )
    boundary_generation = (
        int(boundary_record["generation"])
        if boundary_record is not None else attempted_generations
    )
    boundary_evaluation_calls = (
        int(boundary_record["evaluation_calls"])
        if boundary_record is not None else int(problem.evaluation_calls)
    )
    convergence.append({
        "generation": boundary_generation,
        "evaluation_calls": boundary_evaluation_calls,
        "effective_independent_evaluations": target_budget,
        **quality_summary(epsilon_front, getattr(study, "objective_config", {})),
    })
    return candidates, epsilon_front, {
        "backend": "nsga2_parameter_baseline",
        "population": population,
        "generations": generations,
        "generations_executed": attempted_generations,
        "effective_evaluation_budget": target_budget,
        "unique_evaluations": target_budget,
        "raw_unique_evaluations": len(problem.evaluations),
        "discarded_unique_evaluations": max(0, len(active) - target_budget),
        "cache_hits": int(problem.evaluation_calls - len(problem.evaluations)),
        "uses_stakeholder_categories": False,
        "uses_scenario_permissions": False,
        "parameter_ranges": baseline_config.get("baseline", baseline_config).get("parameters", {}),
        "maximum_changed_buildings": problem.maximum_changed_buildings,
        "shared_hard_constraints": True,
        "full_pareto_solution_ids": [item.solution_id for item in full_front],
        "epsilon_pareto_solution_ids": [item.solution_id for item in epsilon_front],
        "representative_solution_ids": [item.solution_id for item in representatives],
        "pareto_diagnostics": diagnostics,
        "convergence": convergence,
    }

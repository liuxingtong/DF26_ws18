from __future__ import annotations

import random
from typing import Any

from .constraints import check_constraints
from .metrics import quality_summary
from .models import CandidateEvaluation, ZoneDecision
from .objectives import build_objective_context, evaluate_objectives
from .operators import (
    apply_decisions,
    build_operator_availability,
    operator_policy,
)
from .pareto import morphology_signature, pareto_sets


def _sample_decisions(
    zone_ids: list[str], rng: random.Random, max_changed_ratio: float,
    availability: dict[str, tuple[str, ...]] | None = None,
    intensity_limits: dict[str, float] | None = None,
) -> list[ZoneDecision]:
    max_changed = max(1, round(len(zone_ids) * max_changed_ratio))
    changed = set(rng.sample(zone_ids, k=rng.randint(1, min(max_changed, len(zone_ids)))))
    decisions = []
    for zone_id in zone_ids:
        if zone_id not in changed:
            decisions.append(ZoneDecision(zone_id, "noop", 0.0))
        else:
            choices = [
                item for item in (availability or {}).get(zone_id, ("densify", "open_ground"))
                if item != "noop"
            ]
            if choices:
                operator = rng.choice(choices)
                limit = (intensity_limits or {}).get(operator, 1.0)
                decisions.append(ZoneDecision(zone_id, operator, rng.random() * limit))
            else:
                decisions.append(ZoneDecision(zone_id, "noop", 0.0))
    return decisions


def evaluate_candidate(
    study,
    decisions: list[ZoneDecision],
    operator_specs: dict[str, Any],
    solution_id: str,
    objective_context=None,
):
    objective_config = getattr(study, "objective_config", {})
    candidate, changes = apply_decisions(
        study.buildings, decisions, study.controls, operator_specs, study.zones,
        scenario=study.scenario,
        minimum_change=objective_config.get("numerical_resolution", {}),
    )
    violations = check_constraints(
        study.buildings, candidate, study.boundary, study.zones, study.controls, study.scenario
    )
    objectives, descriptors = evaluate_objectives(
        study.buildings, candidate, changes, study.boundary, study.streets, study.scenario,
        context=objective_context, objective_config=objective_config,
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


def decision_key(decisions: list[ZoneDecision]) -> tuple:
    return tuple((item.zone_id, item.operator, round(item.intensity, 6)) for item in decisions)


def run_random_baseline(
    study,
    operator_specs: dict[str, Any],
    *,
    samples: int = 100,
    seed: int = 42,
    unique_samples: bool = True,
):
    if study.blockers:
        raise RuntimeError("正式运行被数据审计阻止：" + "；".join(study.blockers))
    if study.zones is None or study.zones.empty:
        raise RuntimeError("没有可用更新单元")
    zone_ids = sorted(study.zones["zone_id"].astype(str).unique())
    max_changed_ratio = float(study.scenario.get("implementation", {}).get("maximum_changed_zone_ratio", 0.40))
    rng = random.Random(seed)
    availability = build_operator_availability(
        study.buildings, study.zones, study.controls, study.scenario
    )
    _, _, intensity_limits = operator_policy(study.scenario)
    candidates = []
    objective_context = build_objective_context(
        study.buildings, study.boundary, study.streets, study.scenario,
        getattr(study, "objective_config", {}),
    )
    # Include the current city as a reproducible reference candidate.
    baseline_decisions = [ZoneDecision(zone_id, "noop", 0.0) for zone_id in zone_ids]
    candidates.append(evaluate_candidate(
        study, baseline_decisions, operator_specs, "S_0000", objective_context
    ))
    seen: set[tuple] = {decision_key(baseline_decisions)}
    seen_morphologies: set[str] = set()
    attempts = 0
    maximum_attempts = max(samples * 100, 1000)
    while len(candidates) - 1 < samples:
        attempts += 1
        if attempts > maximum_attempts:
            raise RuntimeError(f"无法在 {maximum_attempts} 次抽样内得到 {samples} 个独立随机候选")
        decisions = _sample_decisions(
            zone_ids, rng, max_changed_ratio, availability,
            intensity_limits,
        )
        key = decision_key(decisions)
        if unique_samples and key in seen:
            continue
        if unique_samples:
            seen.add(key)
        index = len(candidates)
        candidate = evaluate_candidate(
            study, decisions, operator_specs, f"S_{index:04d}", objective_context
        )
        morphology = morphology_signature(candidate)
        if unique_samples and (not candidate.has_effective_change or morphology in seen_morphologies):
            continue
        seen_morphologies.add(morphology)
        candidates.append(candidate)
    full_front, epsilon_front, representatives, diagnostics = pareto_sets(
        candidates, getattr(study, "objective_config", {})
    )
    metadata = {
        "backend": "random",
        "requested_independent_evaluations": samples,
        "effective_independent_evaluations": len(candidates) - 1,
        "sampling_attempts": attempts,
        "unique_evaluations": samples,
        "effective_evaluation_budget": samples,
        "full_pareto_solution_ids": [item.solution_id for item in full_front],
        "epsilon_pareto_solution_ids": [item.solution_id for item in epsilon_front],
        "representative_solution_ids": [item.solution_id for item in representatives],
        "pareto_diagnostics": diagnostics,
        "building_scope_repair_enabled": False,
        "convergence": [{
            "generation": 0,
            "evaluation_calls": attempts,
            "effective_independent_evaluations": len(candidates) - 1,
            **quality_summary(epsilon_front, getattr(study, "objective_config", {})),
        }],
    }
    return candidates, epsilon_front, metadata

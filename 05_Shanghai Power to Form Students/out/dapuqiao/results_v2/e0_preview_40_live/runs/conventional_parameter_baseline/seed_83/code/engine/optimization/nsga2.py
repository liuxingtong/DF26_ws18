from __future__ import annotations

import math
from typing import Any

import numpy as np
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.callback import Callback
from pymoo.core.crossover import Crossover
from pymoo.core.mutation import Mutation
from pymoo.core.problem import ElementwiseProblem
from pymoo.core.sampling import Sampling
from pymoo.core.termination import Termination
from pymoo.optimize import minimize

from .metrics import quality_summary
from .models import ZoneDecision
from .objectives import build_objective_context
from .operators import build_operator_availability, operator_policy
from .pareto import morphology_signature, pareto_sets
from .search import evaluate_candidate


OPERATOR_NAMES = (
    "noop",
    "densify",
    "open_ground",
    "split_to_towers",
    "heritage_step_down",
    "public_space_reconfiguration",
    "courtyard_access_improvement",
)


def _random_generator(kwargs):
    """Support both pymoo's legacy global RNG and newer random_state API."""
    return kwargs.get("random_state") or np.random


def _integers(rng, low, high=None, size=None):
    if hasattr(rng, "integers"):
        return rng.integers(low, high, size=size)
    return rng.randint(low, high, size=size)


def _decode_vector(
    vector, zone_ids: list[str], maximum_changed_ratio: float,
    availability: dict[str, tuple[str, ...]] | None = None,
    intensity_limits: dict[str, float] | None = None,
) -> list[ZoneDecision]:
    decisions = []
    for index, zone_id in enumerate(zone_ids):
        operator_index = int(np.clip(round(float(vector[index * 2])), 0, len(OPERATOR_NAMES) - 1))
        operator = OPERATOR_NAMES[operator_index]
        if availability is not None and operator not in availability.get(zone_id, ("noop",)):
            operator = "noop"
        maximum_intensity = (intensity_limits or {}).get(operator, 1.0)
        intensity = float(np.clip(vector[index * 2 + 1], 0.0, maximum_intensity))
        if operator == "noop":
            intensity = 0.0
        decisions.append(ZoneDecision(zone_id, operator, intensity))

    maximum_changed = max(1, round(len(zone_ids) * maximum_changed_ratio))
    changed = [index for index, item in enumerate(decisions) if item.operator != "noop"]
    if len(changed) > maximum_changed:
        keep = set(sorted(changed, key=lambda index: decisions[index].intensity, reverse=True)[:maximum_changed])
        decisions = [item if index in keep or item.operator == "noop" else ZoneDecision(item.zone_id, "noop", 0.0)
                     for index, item in enumerate(decisions)]
    return decisions


def _decision_key(decisions: list[ZoneDecision]) -> tuple:
    return tuple((item.zone_id, item.operator, round(item.intensity, 6)) for item in decisions)


class MixedDecisionSampling(Sampling):
    def _do(self, problem, n_samples, **kwargs):
        rng = _random_generator(kwargs)
        matrix = np.empty((n_samples, problem.n_var), dtype=float)
        for column in range(0, problem.n_var, 2):
            matrix[:, column] = _integers(rng, 0, len(OPERATOR_NAMES), size=n_samples)
            matrix[:, column + 1] = rng.random(n_samples)
        # Seed interpretable reference points so even small smoke runs exercise feasible alternatives.
        if n_samples >= 1:
            matrix[0, 0::2] = 0
            matrix[0, 1::2] = 0
        if n_samples >= 2:
            matrix[1, 0::2] = 2
            matrix[1, 1::2] = 0.5
        if n_samples >= 3:
            matrix[2, 0::2] = 1
            matrix[2, 1::2] = 0.2
        if n_samples >= 4:
            matrix[3, 0::2] = 3
            matrix[3, 1::2] = 0.5
        if n_samples >= 5:
            matrix[4, 0::2] = 4
            matrix[4, 1::2] = 0.5
        if n_samples >= 6:
            matrix[5, 0::2] = 5
            matrix[5, 1::2] = 0.5
        if n_samples >= 7:
            matrix[6, 0::2] = 6
            matrix[6, 1::2] = 0.5
        return matrix


class MixedDecisionCrossover(Crossover):
    def __init__(self, probability: float = 0.9):
        super().__init__(2, 2)
        self.probability = probability

    def _do(self, problem, X, **kwargs):
        rng = _random_generator(kwargs)
        _, n_matings, n_var = X.shape
        children = np.empty((2, n_matings, n_var), dtype=float)
        for mating in range(n_matings):
            first, second = X[0, mating].copy(), X[1, mating].copy()
            if rng.random() <= self.probability:
                zone_count = n_var // 2
                cut = _integers(rng, 1, zone_count) if zone_count > 1 else 1
                pivot = cut * 2
                first[pivot:], second[pivot:] = second[pivot:].copy(), first[pivot:].copy()
            children[0, mating], children[1, mating] = first, second
        return children


class MixedDecisionMutation(Mutation):
    def __init__(self, probability: float | None = None):
        super().__init__()
        self.probability = probability

    def _do(self, problem, X, **kwargs):
        rng = _random_generator(kwargs)
        result = X.copy()
        zone_probability = self.probability or min(0.25, 1.0 / max(problem.zone_count, 1))
        for row in range(len(result)):
            for zone_index in range(problem.zone_count):
                column = zone_index * 2
                if rng.random() < zone_probability:
                    result[row, column] = _integers(rng, 0, len(OPERATOR_NAMES))
                if rng.random() < zone_probability:
                    result[row, column + 1] = np.clip(
                        result[row, column + 1] + rng.normal(0.0, 0.15), 0.0, 1.0
                    )
        return result


class DapuqiaoNSGA2Problem(ElementwiseProblem):
    def __init__(self, study, operator_specs: dict[str, Any]):
        self.study = study
        self.operator_specs = operator_specs
        self.zone_ids = sorted(study.zones["zone_id"].astype(str).unique())
        self.zone_count = len(self.zone_ids)
        self.maximum_changed_ratio = float(
            study.scenario.get("implementation", {}).get("maximum_changed_zone_ratio", 0.40)
        )
        self.operator_availability = build_operator_availability(
            study.buildings, study.zones, study.controls, study.scenario,
            operator_specs,
        )
        _, _, self.intensity_limits = operator_policy(study.scenario)
        maximum_building_ratio = float(
            study.scenario.get("implementation", {}).get("maximum_changed_building_ratio", 1.0)
        )
        self.maximum_changed_buildings = math.floor(len(study.buildings) * maximum_building_ratio)
        self.objective_context = build_objective_context(
            study.buildings, study.boundary, study.streets, study.scenario,
            getattr(study, "objective_config", {}),
        )
        self.cache = {}
        self.evaluations = []
        self.evaluation_calls = 0
        lower = np.tile([0.0, 0.0], self.zone_count)
        upper = np.tile([float(len(OPERATOR_NAMES) - 1), 1.0], self.zone_count)
        super().__init__(n_var=self.zone_count * 2, n_obj=3, n_ieq_constr=1, xl=lower, xu=upper)

    def _evaluate(self, vector, out, *args, **kwargs):
        self.evaluation_calls += 1
        decisions = _decode_vector(
            vector, self.zone_ids, self.maximum_changed_ratio, self.operator_availability,
            self.intensity_limits,
        )
        key = _decision_key(decisions)
        candidate = self.cache.get(key)
        if candidate is None:
            candidate = evaluate_candidate(
                self.study,
                decisions,
                self.operator_specs,
                f"N_{len(self.evaluations) + 1:05d}",
                self.objective_context,
            )
            self.cache[key] = candidate
            self.evaluations.append(candidate)
        out["F"] = np.asarray(candidate.minimization_vector(), dtype=float)
        out["G"] = np.asarray([sum(item.severity == "blocking" for item in candidate.violations)], dtype=float)


class ConvergenceRecorder(Callback):
    def __init__(self, objective_config: dict):
        super().__init__()
        self.objective_config = objective_config
        self.records: list[dict[str, float | int]] = []

    def notify(self, algorithm) -> None:
        problem = algorithm.problem
        _, front, _, _ = pareto_sets(problem.evaluations, self.objective_config)
        active_count = len({
            morphology_signature(candidate)
            for candidate in problem.evaluations if candidate.has_effective_change
        })
        self.records.append({
            "generation": int(algorithm.n_gen),
            "evaluation_calls": int(problem.evaluation_calls),
            "effective_independent_evaluations": int(active_count),
            **quality_summary(front, self.objective_config),
        })


class IndependentEvaluationTermination(Termination):
    """Stop after a target number of distinct, effective morphologies."""

    def __init__(self, target: int, maximum_generations: int):
        super().__init__()
        self.target = target
        self.maximum_generations = maximum_generations

    def _update(self, algorithm) -> float:
        unique = {
            morphology_signature(candidate)
            for candidate in algorithm.problem.evaluations
            if candidate.has_effective_change
        }
        if len(unique) >= self.target:
            return 1.0
        if int(algorithm.n_gen or 0) >= self.maximum_generations:
            return 1.0
        return min(len(unique) / self.target, 0.999999)


def run_nsga2(
    study,
    operator_specs: dict[str, Any],
    *,
    population: int = 40,
    generations: int = 20,
    seed: int = 42,
    evaluation_budget: int | None = None,
):
    if study.blockers:
        raise RuntimeError("正式运行被数据审计阻止：" + "；".join(study.blockers))
    if study.zones is None or study.zones.empty:
        raise RuntimeError("没有可用更新单元")
    target_budget = evaluation_budget or population * generations
    if target_budget < 1:
        raise ValueError("evaluation_budget 必须为正")
    problem = DapuqiaoNSGA2Problem(study, operator_specs)
    recorder = ConvergenceRecorder(getattr(study, "objective_config", {}))
    algorithm = NSGA2(
        pop_size=population,
        sampling=MixedDecisionSampling(),
        crossover=MixedDecisionCrossover(),
        mutation=MixedDecisionMutation(),
        eliminate_duplicates=True,
    )
    maximum_generations = max(generations * 20, generations + 200)
    result = minimize(
        problem,
        algorithm,
        termination=IndependentEvaluationTermination(target_budget, maximum_generations),
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
    if len(active) < target_budget:
        raise RuntimeError(
            f"NSGA-II 在 {maximum_generations} 代内只能生成 {len(active)} 个独立非空候选，"
            f"未达到预算 {target_budget}"
        )
    attempted_generations = int(result.algorithm.n_gen - 1)
    baseline = evaluate_candidate(
        study,
        [ZoneDecision(zone_id, "noop", 0.0) for zone_id in problem.zone_ids],
        operator_specs,
        "S_0000",
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
        "backend": "nsga2",
        "population": population,
        "generations": generations,
        "generations_executed": attempted_generations,
        "effective_evaluation_budget": target_budget,
        "unique_evaluations": target_budget,
        "raw_unique_evaluations": len(problem.evaluations),
        "discarded_unique_evaluations": max(0, len(active) - target_budget),
        "cache_hits": int(problem.evaluation_calls - len(problem.evaluations)),
        "operator_availability": {
            zone_id: list(operators)
            for zone_id, operators in problem.operator_availability.items()
        },
        "operator_policy": study.scenario.get("operator_policy", {}),
        "maximum_changed_buildings": problem.maximum_changed_buildings,
        "building_scope_repair_enabled": False,
        "full_pareto_solution_ids": [item.solution_id for item in full_front],
        "epsilon_pareto_solution_ids": [item.solution_id for item in epsilon_front],
        "representative_solution_ids": [item.solution_id for item in representatives],
        "pareto_diagnostics": diagnostics,
        "convergence": convergence,
    }

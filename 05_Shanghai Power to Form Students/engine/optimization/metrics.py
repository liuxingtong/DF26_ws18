from __future__ import annotations

from copy import deepcopy

import numpy as np
from pymoo.indicators.hv import HV
from scipy.stats import rankdata, wilcoxon

from .models import CandidateEvaluation
from .pareto import OBJECTIVE_NAMES, dominates, normalised_cost, pareto_sets


OBJECTIVE_DIRECTIONS = {
    "residential_disruption": "minimize",
    "development_capacity": "maximize",
    "street_connected_released_ground": "maximize",
}


def normalised_matrix(front: list[CandidateEvaluation], config: dict) -> np.ndarray:
    if not front:
        return np.empty((0, 3), dtype=float)
    return np.asarray([normalised_cost(item, config) for item in front], dtype=float)


def hypervolume(
    front: list[CandidateEvaluation],
    config: dict,
    reference_point: tuple[float, float, float] = (1.1, 1.1, 1.1),
) -> float:
    matrix = normalised_matrix(front, config)
    if not len(matrix):
        return 0.0
    return float(HV(ref_point=np.asarray(reference_point, dtype=float))(matrix))


def spacing(front: list[CandidateEvaluation], config: dict) -> float:
    """Schott spacing on fixed-reference normalised objectives; lower is even."""
    matrix = normalised_matrix(front, config)
    if len(matrix) < 2:
        return 0.0
    distances = []
    for index, row in enumerate(matrix):
        others = np.delete(matrix, index, axis=0)
        distances.append(float(np.min(np.abs(others - row).sum(axis=1))))
    return float(np.std(distances, ddof=1)) if len(distances) > 1 else 0.0


def coverage(first: list[CandidateEvaluation], second: list[CandidateEvaluation]) -> float:
    """C(first, second): fraction of second exactly dominated by first."""
    if not second:
        return 0.0
    return float(
        sum(any(dominates(a, b) for a in first) for b in second) / len(second)
    )


def quality_summary(front: list[CandidateEvaluation], config: dict) -> dict[str, float | int]:
    return {
        "pareto_count": len(front),
        "hypervolume": hypervolume(front, config),
        "spacing": spacing(front, config),
    }


def front_distribution(
    front: list[CandidateEvaluation],
    layer: str,
) -> list[dict[str, float | int | str | None]]:
    """Summarize raw objective values for one auditable Pareto layer."""
    rows = []
    for name in OBJECTIVE_NAMES:
        values = np.asarray(
            [float(candidate.objectives[name]) for candidate in front], dtype=float
        )
        if not len(values):
            rows.append({
                "pareto_layer": layer,
                "objective": name,
                "direction": OBJECTIVE_DIRECTIONS[name],
                "solution_count": 0,
                "unique_value_count": 0,
                "zero_fraction": None,
                "minimum": None,
                "q25": None,
                "median": None,
                "mean": None,
                "q75": None,
                "maximum": None,
                "standard_deviation": None,
            })
            continue
        rows.append({
            "pareto_layer": layer,
            "objective": name,
            "direction": OBJECTIVE_DIRECTIONS[name],
            "solution_count": len(values),
            "unique_value_count": int(len(np.unique(values))),
            "zero_fraction": float(np.mean(np.isclose(values, 0.0, atol=1e-12))),
            "minimum": float(np.min(values)),
            "q25": float(np.quantile(values, 0.25)),
            "median": float(np.median(values)),
            "mean": float(np.mean(values)),
            "q75": float(np.quantile(values, 0.75)),
            "maximum": float(np.max(values)),
            "standard_deviation": float(np.std(values, ddof=1)) if len(values) > 1 else 0.0,
        })
    return rows


def paired_wilcoxon(
    baseline_values: list[float],
    comparison_values: list[float],
    *,
    higher_is_better: bool,
) -> dict[str, float | int | str]:
    """Paired signed-rank test with a direction-aware rank-biserial effect."""
    baseline = np.asarray(baseline_values, dtype=float)
    comparison = np.asarray(comparison_values, dtype=float)
    if baseline.shape != comparison.shape or baseline.ndim != 1:
        raise ValueError("paired samples must be one-dimensional and equal length")
    raw_difference = comparison - baseline
    improvement = raw_difference if higher_is_better else -raw_difference
    nonzero = improvement[~np.isclose(improvement, 0.0, atol=1e-15)]
    if len(nonzero):
        ranks = rankdata(np.abs(nonzero), method="average")
        positive = float(ranks[nonzero > 0].sum())
        negative = float(ranks[nonzero < 0].sum())
        denominator = positive + negative
        effect = (positive - negative) / denominator if denominator else 0.0
        test = wilcoxon(nonzero, alternative="two-sided", method="auto")
        statistic = float(test.statistic)
        p_value = float(test.pvalue)
    else:
        effect = 0.0
        statistic = 0.0
        p_value = 1.0
    return {
        "pair_count": int(len(improvement)),
        "nonzero_pair_count": int(len(nonzero)),
        "comparison_wins": int((improvement > 0).sum()),
        "ties": int(np.isclose(improvement, 0.0, atol=1e-15).sum()),
        "comparison_losses": int((improvement < 0).sum()),
        "median_raw_difference": float(np.median(raw_difference)),
        "median_directional_improvement": float(np.median(improvement)),
        "rank_biserial_effect": float(effect),
        "wilcoxon_statistic": statistic,
        "p_value_two_sided": p_value,
        "test": "paired Wilcoxon signed-rank",
    }


def holm_adjust(p_values: list[float]) -> list[float]:
    """Holm family-wise correction, preserving the caller's row order."""
    count = len(p_values)
    order = sorted(range(count), key=lambda index: p_values[index])
    adjusted = [1.0] * count
    running = 0.0
    for rank, index in enumerate(order):
        value = min(1.0, (count - rank) * float(p_values[index]))
        running = max(running, value)
        adjusted[index] = running
    return adjusted


def epsilon_sensitivity(
    candidates: list[CandidateEvaluation],
    config: dict,
    factors: tuple[float, ...] = (0.5, 1.0, 2.0),
) -> list[dict[str, float | int]]:
    rows = []
    base_epsilon = config.get("epsilon", {})
    for factor in factors:
        varied = deepcopy(config)
        varied["epsilon"] = {
            key: float(value) * factor for key, value in base_epsilon.items()
        }
        full, front, representatives, diagnostics = pareto_sets(candidates, varied)
        rows.append({
            "epsilon_factor": factor,
            **{f"epsilon_{key}": value for key, value in varied["epsilon"].items()},
            "full_pareto_count": len(full),
            "epsilon_pareto_count": len(front),
            "representative_count": len(representatives),
            "objective_duplicate_count": diagnostics["objective_duplicate_count"],
            **quality_summary(front, config),
        })
    return rows


def normalization_bounds(fronts) -> tuple[np.ndarray, np.ndarray]:
    """Compatibility helper for method-only comparisons within one measurement frame."""
    vectors = [item.minimization_vector() for front in fronts for item in front]
    if not vectors:
        return np.zeros(3), np.ones(3)
    matrix = np.asarray(vectors, dtype=float)
    return matrix.min(axis=0), matrix.max(axis=0)


def front_metrics(
    front: list[CandidateEvaluation],
    config_or_ideal,
    nadir: np.ndarray | None = None,
) -> dict[str, float]:
    """Quality indicators with fixed config bounds or explicit pooled bounds."""
    if nadir is None:
        return {
            "hypervolume": hypervolume(front, config_or_ideal),
            "spacing": spacing(front, config_or_ideal),
        }
    if not front:
        return {"hypervolume": 0.0, "spacing": 0.0}
    ideal = np.asarray(config_or_ideal, dtype=float)
    nadir = np.asarray(nadir, dtype=float)
    span = np.maximum(nadir - ideal, 1e-12)
    matrix = np.asarray([item.minimization_vector() for item in front], dtype=float)
    matrix = np.clip((matrix - ideal) / span, 0.0, 1.0)
    hv = float(HV(ref_point=np.asarray([1.1, 1.1, 1.1]))(matrix))
    if len(matrix) < 2:
        space = 0.0
    else:
        nearest = []
        for index, row in enumerate(matrix):
            others = np.delete(matrix, index, axis=0)
            nearest.append(float(np.min(np.abs(others - row).sum(axis=1))))
        space = float(np.std(nearest, ddof=1))
    return {"hypervolume": hv, "spacing": space}

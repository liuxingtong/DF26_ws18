from __future__ import annotations

from typing import Any

from .models import CandidateEvaluation


OBJECTIVE_DIRECTION = {
    "residential_disruption": "minimize",
    "development_capacity": "maximize",
    "street_connected_released_ground": "maximize",
}

DEFAULT_REFERENCE_BOUNDS = {
    "residential_disruption": {"minimum": 0.0, "maximum": 0.35},
    "development_capacity": {"minimum": 0.0, "maximum": 0.01},
    "street_connected_released_ground": {"minimum": 0.0, "maximum": 0.0025},
}


def _desirability(
    candidates: list[CandidateEvaluation],
    reference_bounds: dict[str, Any] | None = None,
) -> dict[str, dict[str, float]]:
    reference_bounds = reference_bounds or DEFAULT_REFERENCE_BOUNDS
    result = {candidate.solution_id: {} for candidate in candidates}
    for key, direction in OBJECTIVE_DIRECTION.items():
        bound = reference_bounds.get(key, DEFAULT_REFERENCE_BOUNDS[key])
        low = float(bound["minimum"])
        high = float(bound["maximum"])
        span = high - low
        for candidate in candidates:
            value = candidate.objectives[key]
            scaled = 0.5 if span <= 1e-12 else (value - low) / span
            scaled = min(max(float(scaled), 0.0), 1.0)
            result[candidate.solution_id][key] = 1.0 - scaled if direction == "minimize" else scaled
    return result


def evaluate_roles(
    candidates: list[CandidateEvaluation],
    role_config: dict[str, Any],
    reference_bounds: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    if not candidates:
        return [], {}
    desirability = _desirability(candidates, reference_bounds)
    rows: list[dict[str, Any]] = []
    role_best: dict[str, str] = {}
    scores_by_solution: dict[str, list[float]] = {candidate.solution_id: [] for candidate in candidates}

    for role_name, profile in role_config.get("roles", {}).items():
        weights = profile.get("weights", {})
        thresholds = profile.get("thresholds", {})
        role_rows = []
        for candidate in candidates:
            score = sum(float(weights.get(key, 0.0)) * desirability[candidate.solution_id][key]
                        for key in OBJECTIVE_DIRECTION)
            accepted = candidate.feasible
            maximum = thresholds.get("residential_disruption_max")
            if maximum is not None and candidate.objectives["residential_disruption"] > float(maximum):
                accepted = False
            row = {
                "role": role_name,
                "role_label": profile.get("label", role_name),
                "solution_id": candidate.solution_id,
                "score": float(score),
                "accepted": bool(accepted),
            }
            role_rows.append(row)
            scores_by_solution[candidate.solution_id].append(float(score))
        role_rows.sort(key=lambda row: (not row["accepted"], -row["score"], row["solution_id"]))
        for rank, row in enumerate(role_rows, start=1):
            row["rank"] = rank
        rows.extend(role_rows)
        accepted_rows = [row for row in role_rows if row["accepted"]]
        if accepted_rows:
            role_best[role_name] = accepted_rows[0]["solution_id"]

    # Maximin desirability: choose the solution whose weakest role score is highest.
    compromise = max(
        candidates,
        key=lambda candidate: (min(scores_by_solution[candidate.solution_id]),
                               sum(scores_by_solution[candidate.solution_id])),
    )
    role_best["balanced_compromise"] = compromise.solution_id
    return rows, role_best


def evaluate_role_sensitivity(
    candidates: list[CandidateEvaluation],
    role_config: dict[str, Any],
    reference_bounds: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """One-at-a-time weight and threshold sensitivity for audit, not optimisation."""
    if not candidates:
        return []
    sensitivity = role_config.get("sensitivity", {})
    weight_factors = [float(value) for value in sensitivity.get("weight_factors", [0.8, 1.2])]
    threshold_factors = [
        float(value) for value in sensitivity.get("threshold_factors", [0.8, 1.2])
    ]
    rows: list[dict[str, Any]] = []
    for role_name, profile in role_config.get("roles", {}).items():
        variants: list[tuple[str, str, float, dict[str, Any]]] = [
            ("base", "none", 1.0, profile)
        ]
        for objective in OBJECTIVE_DIRECTION:
            for factor in weight_factors:
                varied = {
                    **profile,
                    "weights": dict(profile.get("weights", {})),
                    "thresholds": dict(profile.get("thresholds", {})),
                }
                varied["weights"][objective] = float(varied["weights"].get(objective, 0.0)) * factor
                total = sum(float(value) for value in varied["weights"].values())
                if total > 0:
                    varied["weights"] = {
                        key: float(value) / total for key, value in varied["weights"].items()
                    }
                variants.append(("weight", objective, factor, varied))
        threshold = profile.get("thresholds", {}).get("residential_disruption_max")
        if threshold is not None:
            for factor in threshold_factors:
                varied = {
                    **profile,
                    "weights": dict(profile.get("weights", {})),
                    "thresholds": dict(profile.get("thresholds", {})),
                }
                varied["thresholds"]["residential_disruption_max"] = float(threshold) * factor
                variants.append(("threshold", "residential_disruption_max", factor, varied))

        for variant_type, parameter, factor, varied_profile in variants:
            local_config = {"roles": {role_name: varied_profile}}
            ranking, selection = evaluate_roles(candidates, local_config, reference_bounds)
            role_rows = [row for row in ranking if row["role"] == role_name]
            rows.append({
                "role": role_name,
                "variant_type": variant_type,
                "parameter": parameter,
                "factor": factor,
                "selected_solution_id": selection.get(role_name),
                "accepted_count": sum(bool(row["accepted"]) for row in role_rows),
                "selected_score": next(
                    (row["score"] for row in role_rows if row["solution_id"] == selection.get(role_name)),
                    None,
                ),
            })
    return rows

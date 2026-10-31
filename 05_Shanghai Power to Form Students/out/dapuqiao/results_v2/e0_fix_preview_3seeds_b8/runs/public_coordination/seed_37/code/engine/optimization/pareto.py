from __future__ import annotations

import hashlib

import numpy as np

from .models import CandidateEvaluation


OBJECTIVE_NAMES = (
    "residential_disruption",
    "development_capacity",
    "street_connected_released_ground",
)


def epsilon_vector(config: dict | None = None) -> tuple[float, float, float]:
    values = (config or {}).get("epsilon", {})
    return tuple(float(values.get(name, 0.0)) for name in OBJECTIVE_NAMES)


def dominates(
    a: CandidateEvaluation,
    b: CandidateEvaluation,
    tolerance: float = 1e-12,
) -> bool:
    if not a.feasible:
        return False
    if not b.feasible:
        return True
    av = a.minimization_vector()
    bv = b.minimization_vector()
    no_worse = all(x <= y + tolerance for x, y in zip(av, bv))
    strictly_better = any(x < y - tolerance for x, y in zip(av, bv))
    return no_worse and strictly_better


def epsilon_dominates(
    a: CandidateEvaluation,
    b: CandidateEvaluation,
    epsilon: tuple[float, float, float],
) -> bool:
    """Additive epsilon dominance in the common minimization orientation."""
    if not a.feasible:
        return False
    if not b.feasible:
        return True
    av = a.minimization_vector()
    bv = b.minimization_vector()
    no_worse = all(x <= y + eps for x, y, eps in zip(av, bv, epsilon))
    meaningfully_better = any(x < y - eps for x, y, eps in zip(av, bv, epsilon))
    return no_worse and meaningfully_better


def nondominated(
    candidates: list[CandidateEvaluation],
    epsilon: tuple[float, float, float] | None = None,
) -> list[CandidateEvaluation]:
    feasible = [candidate for candidate in candidates if candidate.feasible]
    relation = (
        (lambda first, second: epsilon_dominates(first, second, epsilon))
        if epsilon is not None
        else dominates
    )
    return [
        candidate
        for candidate in feasible
        if not any(relation(other, candidate) for other in feasible if other is not candidate)
    ]


def morphology_signature(candidate: CandidateEvaluation) -> str:
    """Hash the resulting changed morphology, not the encoded decision vector."""
    digest = hashlib.sha256()
    changed_ids = sorted(str(item["bid"]) for item in candidate.changes)
    digest.update("|".join(changed_ids).encode("utf-8"))
    if candidate.buildings is None or not changed_ids:
        for change in sorted(candidate.changes, key=lambda item: str(item["bid"])):
            digest.update(
                (
                    f"{change['bid']}:{float(change.get('after_height_m', 0.0)):.9f}:"
                    f"{float(change.get('after_area_m2', 0.0)):.9f}"
                ).encode("utf-8")
            )
        return digest.hexdigest()
    changed = candidate.buildings[
        candidate.buildings["bid"].astype(str).isin(changed_ids)
    ].copy()
    changed["_bid"] = changed["bid"].astype(str)
    for _, row in changed.sort_values("_bid").iterrows():
        digest.update(row["_bid"].encode("utf-8"))
        digest.update(f"{float(row['height_m']):.9f}".encode("ascii"))
        geometry = row.geometry.normalize() if hasattr(row.geometry, "normalize") else row.geometry
        digest.update(geometry.wkb)
    return digest.hexdigest()


def normalised_cost(candidate: CandidateEvaluation, config: dict) -> np.ndarray:
    bounds = config.get("normalization_reference", {})
    result = []
    for index, name in enumerate(OBJECTIVE_NAMES):
        bound = bounds.get(name, {})
        low = float(bound.get("minimum", 0.0))
        high = float(bound.get("maximum", 1.0))
        span = max(high - low, 1e-12)
        value = float(candidate.objectives[name])
        scaled = (value - low) / span
        if index > 0:
            scaled = 1.0 - scaled
        result.append(float(np.clip(scaled, 0.0, 1.0)))
    return np.asarray(result, dtype=float)


def _deduplicate_morphology(
    candidates: list[CandidateEvaluation],
) -> tuple[list[CandidateEvaluation], int]:
    unique: dict[str, CandidateEvaluation] = {}
    for candidate in sorted(candidates, key=lambda item: item.solution_id):
        unique.setdefault(morphology_signature(candidate), candidate)
    return list(unique.values()), len(candidates) - len(unique)


def _deduplicate_objectives(
    candidates: list[CandidateEvaluation],
    epsilon: tuple[float, float, float],
    config: dict,
) -> tuple[list[CandidateEvaluation], int]:
    ordered = sorted(
        candidates,
        key=lambda item: (float(normalised_cost(item, config).sum()), item.solution_id),
    )
    kept: list[CandidateEvaluation] = []
    for candidate in ordered:
        vector = candidate.minimization_vector()
        if any(
            all(abs(x - y) <= eps for x, y, eps in zip(vector, other.minimization_vector(), epsilon))
            for other in kept
        ):
            continue
        kept.append(candidate)
    return kept, len(candidates) - len(kept)


def representative_sample(
    front: list[CandidateEvaluation],
    config: dict,
    maximum: int | None = None,
) -> list[CandidateEvaluation]:
    if not front:
        return []
    limit = int(
        maximum
        or config.get("representative_sampling", {}).get("maximum_solutions", 9)
    )
    if len(front) <= limit:
        return sorted(front, key=lambda item: item.solution_id)
    costs = np.asarray([normalised_cost(item, config) for item in front])
    selected: list[int] = []
    for objective_index in range(costs.shape[1]):
        selected.append(int(np.argmin(costs[:, objective_index])))
    selected.append(int(np.argmin(np.linalg.norm(costs, axis=1))))
    selected = list(dict.fromkeys(selected))
    while len(selected) < limit:
        remaining = [index for index in range(len(front)) if index not in selected]
        next_index = max(
            remaining,
            key=lambda index: min(
                float(np.linalg.norm(costs[index] - costs[chosen])) for chosen in selected
            ),
        )
        selected.append(next_index)
    return [front[index] for index in selected]


def pareto_sets(
    candidates: list[CandidateEvaluation],
    config: dict | None = None,
) -> tuple[
    list[CandidateEvaluation],
    list[CandidateEvaluation],
    list[CandidateEvaluation],
    dict[str, int],
]:
    """Return auditable exact, epsilon-filtered, and display-sized fronts."""
    config = config or {}
    feasible = [candidate for candidate in candidates if candidate.feasible]
    morphology_unique, morphology_duplicates = _deduplicate_morphology(feasible)
    full_front = nondominated(morphology_unique)
    eps = epsilon_vector(config)
    objective_unique, objective_duplicates = _deduplicate_objectives(full_front, eps, config)
    epsilon_front = nondominated(objective_unique, epsilon=eps)
    representatives = representative_sample(epsilon_front, config)
    diagnostics = {
        "input_feasible_count": len(feasible),
        "morphology_duplicate_count": morphology_duplicates,
        "full_pareto_count": len(full_front),
        "objective_duplicate_count": objective_duplicates,
        "epsilon_pareto_count": len(epsilon_front),
        "representative_count": len(representatives),
    }
    return full_front, epsilon_front, representatives, diagnostics

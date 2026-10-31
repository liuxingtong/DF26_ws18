from __future__ import annotations

from typing import Any

from .models import CandidateEvaluation


OBJECTIVE_DIRECTION = {
    "residential_disruption": "minimize",
    "development_capacity": "maximize",
    "street_connected_released_ground": "maximize",
}

DEFAULT_PRIORITY_ORDER = tuple(OBJECTIVE_DIRECTION)


def _validate_priority_order(profile: dict[str, Any]) -> tuple[str, ...]:
    order = tuple(profile.get("priority_order", ()))
    if not order:
        raise ValueError("角色配置缺少 priority_order")
    unknown = [name for name in order if name not in OBJECTIVE_DIRECTION]
    duplicate = len(set(order)) != len(order)
    missing = [name for name in OBJECTIVE_DIRECTION if name not in order]
    if unknown or duplicate or missing:
        raise ValueError(
            "priority_order 必须且只能包含三个共同目标；"
            f"unknown={unknown}, duplicate={duplicate}, missing={missing}"
        )
    return order


def _objective_tiers(
    candidates: list[CandidateEvaluation],
    objective: str,
    epsilon: float,
) -> dict[str, int]:
    """Assign deterministic best-first tiers using epsilon as measurement resolution.

    A tier is anchored on its best remaining value. Candidates within epsilon of
    that anchor share a tier, so the relation is stable and transitive.
    """
    reverse = OBJECTIVE_DIRECTION[objective] == "maximize"
    ordered = sorted(
        candidates,
        key=lambda candidate: (
            -float(candidate.objectives[objective])
            if reverse
            else float(candidate.objectives[objective]),
            candidate.solution_id,
        ),
    )
    tiers: dict[str, int] = {}
    tier = 0
    anchor: float | None = None
    tolerance = max(float(epsilon), 0.0)
    for candidate in ordered:
        value = float(candidate.objectives[objective])
        if anchor is None or abs(value - anchor) > tolerance + 1e-12:
            tier += 1
            anchor = value
        tiers[candidate.solution_id] = tier
    return tiers


def _role_rankings(
    candidates: list[CandidateEvaluation],
    role_name: str,
    profile: dict[str, Any],
    epsilon: dict[str, Any],
) -> list[dict[str, Any]]:
    priority_order = _validate_priority_order(profile)
    tiers = {
        objective: _objective_tiers(
            candidates,
            objective,
            float(epsilon.get(objective, 0.0)),
        )
        for objective in OBJECTIVE_DIRECTION
    }
    role_rows: list[dict[str, Any]] = []
    for candidate in candidates:
        accepted = bool(candidate.feasible)
        signature = tuple(
            tiers[objective][candidate.solution_id] for objective in priority_order
        )
        row = {
            "role": role_name,
            "role_label": profile.get("label", role_name),
            "solution_id": candidate.solution_id,
            "accepted": accepted,
            "priority_order": ">".join(priority_order),
            "priority_signature": ">".join(str(value) for value in signature),
            "_sort_key": (not accepted, *signature, candidate.solution_id),
        }
        for index, objective in enumerate(priority_order, start=1):
            row[f"priority_{index}_objective"] = objective
            row[f"priority_{index}_tier"] = tiers[objective][candidate.solution_id]
        role_rows.append(row)
    role_rows.sort(key=lambda row: row["_sort_key"])
    previous_group: tuple[Any, ...] | None = None
    shared_rank = 0
    for position, row in enumerate(role_rows, start=1):
        group = (not bool(row["accepted"]), row["priority_signature"])
        if group != previous_group:
            shared_rank = position
            previous_group = group
        row["rank"] = shared_rank
        row.pop("_sort_key", None)
    return role_rows


def evaluate_roles(
    candidates: list[CandidateEvaluation],
    role_config: dict[str, Any],
    epsilon: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    """Rank one Pareto set with ordinal, epsilon-tiered role priorities.

    The preference model is deliberately post-hoc: it never changes candidate
    generation or Pareto dominance. The balanced compromise minimizes the worst
    rank assigned by any configured role, then the sum of ranks.
    """
    if not candidates:
        return [], {}
    epsilon = epsilon or {}
    rows: list[dict[str, Any]] = []
    role_best: dict[str, str] = {}
    ranks_by_solution: dict[str, list[int]] = {
        candidate.solution_id: [] for candidate in candidates
    }

    for role_name, profile in role_config.get("roles", {}).items():
        role_rows = _role_rankings(candidates, role_name, profile, epsilon)
        rows.extend(role_rows)
        for row in role_rows:
            ranks_by_solution[row["solution_id"]].append(int(row["rank"]))
        accepted_rows = [row for row in role_rows if row["accepted"]]
        if accepted_rows:
            role_best[role_name] = accepted_rows[0]["solution_id"]

    feasible = [candidate for candidate in candidates if candidate.feasible]
    compromise_pool = feasible or candidates
    compromise = min(
        compromise_pool,
        key=lambda candidate: (
            max(ranks_by_solution[candidate.solution_id], default=10**9),
            sum(ranks_by_solution[candidate.solution_id]),
            candidate.solution_id,
        ),
    )
    role_best["balanced_compromise"] = compromise.solution_id
    return rows, role_best


def evaluate_role_priority_sensitivity(
    candidates: list[CandidateEvaluation],
    role_config: dict[str, Any],
    epsilon: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Audit the effect of swapping adjacent ordinal priorities.

    This replaces numeric weight sensitivity. It records whether a role's
    selected solution changes when two neighbouring priority levels swap.
    """
    if not candidates:
        return []
    epsilon = epsilon or {}
    rows: list[dict[str, Any]] = []
    enabled = bool(
        role_config.get("sensitivity", {}).get("adjacent_priority_swaps", True)
    )
    for role_name, profile in role_config.get("roles", {}).items():
        base_order = list(_validate_priority_order(profile))
        variants: list[tuple[str, str, list[str]]] = [
            ("base", "none", base_order)
        ]
        if enabled:
            for index in range(len(base_order) - 1):
                varied = list(base_order)
                varied[index], varied[index + 1] = varied[index + 1], varied[index]
                variants.append(
                    ("adjacent_priority_swap", f"{index + 1}<->{index + 2}", varied)
                )
        for variant_type, parameter, order in variants:
            varied_profile = {**profile, "priority_order": order}
            local_config = {"roles": {role_name: varied_profile}}
            ranking, selection = evaluate_roles(candidates, local_config, epsilon)
            role_rows = [row for row in ranking if row["role"] == role_name]
            selected_id = selection.get(role_name)
            selected_row = next(
                (row for row in role_rows if row["solution_id"] == selected_id),
                None,
            )
            rows.append({
                "role": role_name,
                "variant_type": variant_type,
                "parameter": parameter,
                "priority_order": ">".join(order),
                "selected_solution_id": selected_id,
                "accepted_count": sum(bool(row["accepted"]) for row in role_rows),
                "selected_rank": selected_row["rank"] if selected_row else None,
            })
    return rows


def evaluate_role_sensitivity(
    candidates: list[CandidateEvaluation],
    role_config: dict[str, Any],
    epsilon: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Backward-compatible alias for ordinal priority sensitivity."""
    return evaluate_role_priority_sensitivity(candidates, role_config, epsilon)

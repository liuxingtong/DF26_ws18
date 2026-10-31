from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ZoneDecision:
    zone_id: str
    operator: str
    intensity: float


@dataclass(frozen=True)
class ParameterDecision:
    """Conventional geometry-only controls for one intervention zone."""

    zone_id: str
    height_multiplier: float
    footprint_ratio: float
    operator: str = field(default="parameter", init=False)

    @property
    def intensity(self) -> float:
        """Compatibility value used by generic exporters and change summaries."""
        height_component = max(0.0, (self.height_multiplier - 1.0) / 0.30)
        footprint_component = max(0.0, (1.0 - self.footprint_ratio) / 0.25)
        return min(1.0, max(height_component, footprint_component))


@dataclass(frozen=True)
class ConstraintViolation:
    code: str
    message: str
    severity: str = "blocking"
    action: str = "reject_candidate"
    zone_id: str | None = None
    bid: str | None = None
    value: float | None = None
    limit: float | None = None


@dataclass
class CandidateEvaluation:
    solution_id: str
    decisions: list[ZoneDecision]
    buildings: Any
    changes: list[dict[str, Any]]
    objectives: dict[str, float]
    descriptors: dict[str, float]
    violations: list[ConstraintViolation] = field(default_factory=list)

    @property
    def feasible(self) -> bool:
        return not any(item.severity == "blocking" for item in self.violations)

    def minimization_vector(self) -> tuple[float, float, float]:
        """NSGA-style vector: every component is minimized."""
        return (
            self.objectives["residential_disruption"],
            -self.objectives["development_capacity"],
            -self.objectives["street_connected_released_ground"],
        )

    @property
    def has_effective_change(self) -> bool:
        return bool(self.changes)

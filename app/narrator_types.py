"""Narrator result types."""

from dataclasses import dataclass, field
from uuid import UUID



@dataclass
class AdjudicationResult:
    accepted: bool
    reason: str | None = None


@dataclass
class AcceptedAction:
    user_id: UUID
    character_name: str
    action_type: str
    action_text: str | None


@dataclass
class DeathResult:
    user_id: UUID
    death_summary: str


@dataclass
class ProgressResult:
    deaths: list[DeathResult] = field(default_factory=list)
    arc_phase: str = "beginning"
    mission_complete: bool = False
    all_dead: bool = False

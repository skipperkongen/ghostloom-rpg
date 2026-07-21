"""Narrator result types."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from app.models.story import Exposition


@dataclass
class AdjudicationResult:
    accepted: bool
    reason: str | None = None


@dataclass
class AcceptedAction:
    character_id: UUID
    character_name: str
    action_type: str
    action_text: str | None


@dataclass
class DeathResult:
    character_id: UUID
    death_summary: str


@dataclass
class ProgressResult:
    deaths: list[DeathResult] = field(default_factory=list)
    mission_complete: bool = False
    all_dead: bool = False


@dataclass
class InitStoryResult:
    exposition: Exposition
    narrator_text: str

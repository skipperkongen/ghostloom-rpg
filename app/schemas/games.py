"""Game API schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.story import Exposition, RoundBeat


class CreateGameRequest(BaseModel):
    seed: str = Field(min_length=1)
    api_key_id: UUID
    character_id: UUID


class JoinGameRequest(BaseModel):
    character_id: UUID


class GameSummaryResponse(BaseModel):
    id: UUID
    seed: str
    status: str
    phase: str
    host_user_id: UUID
    round_number: int
    created_at: datetime


class RoundStateResponse(BaseModel):
    status: Literal["actions_pending", "resolving_round", "resolved", "resolution_failed"]
    error_code: int | None = None
    error_code_name: str | None = None
    error_message: str | None = None
    retryable: bool | None = None
    attempt_count: int | None = None


class PlayerRoundStatus(BaseModel):
    character_id: UUID
    user_id: UUID
    display_name: str | None = None
    name: str
    description: str
    is_alive: bool
    life_state: Literal["alive", "dead"]
    death_summary: str | None = None
    action_submitted: bool


class GameDetailResponse(BaseModel):
    id: UUID
    seed: str
    status: Literal["lobby", "active", "ended"]
    phase: Literal["lobby", "player_round", "dm_round", "resolution_failed", "ended"]
    host_user_id: UUID
    end_reason: Literal["all_dead", "mission_complete"] | None = None
    round_number: int
    round_state: RoundStateResponse
    players: list[PlayerRoundStatus]
    exposition: Exposition | None = None
    beats: list[RoundBeat] = Field(default_factory=list)
    created_at: datetime


class SubmitActionRequest(BaseModel):
    action_type: Literal["act", "pass"]
    action_text: str | None = None


class ActionResponse(BaseModel):
    accepted: bool
    reason: str | None = None
    game: GameDetailResponse

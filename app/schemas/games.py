"""Game API schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.story import Beat, Exposition


class CreateGameRequest(BaseModel):
    seed: str = Field(min_length=1)
    api_key_id: UUID


class GameSummaryResponse(BaseModel):
    id: UUID
    seed: str
    status: str
    phase: str
    host_user_id: UUID
    round_number: int
    created_at: datetime


class CharacterAnswer(BaseModel):
    question_id: str
    choice_id: str


class UpdateCharacterRequest(BaseModel):
    character_name: str = Field(min_length=1, max_length=32)
    answers: list[CharacterAnswer] = Field(default_factory=list)


class QuestionChoice(BaseModel):
    id: str
    label: str


class Question(BaseModel):
    id: str
    text: str
    choices: list[QuestionChoice]


class CharacterQuestionnaire(BaseModel):
    questions: list[Question]


class RoundStateResponse(BaseModel):
    status: Literal["actions_pending", "resolving_round", "resolved", "resolution_failed"]
    error_code: int | None = None
    error_code_name: str | None = None
    error_message: str | None = None
    retryable: bool | None = None
    attempt_count: int | None = None


class PlayerRoundStatus(BaseModel):
    user_id: UUID
    display_name: str | None = None
    character_name: str | None = None
    is_alive: bool
    life_state: Literal["alive", "dead"]
    death_round: int | None = None
    death_summary: str | None = None
    action_submitted: bool
    questionnaire_complete: bool = False


class GameDetailResponse(BaseModel):
    id: UUID
    seed: str
    status: Literal["lobby", "active", "ended"]
    phase: Literal["lobby", "player_round", "dm_round", "resolution_failed", "ended"]
    host_user_id: UUID
    arc_phase: Literal["beginning", "middle", "end"]
    end_reason: Literal["all_dead", "mission_complete"] | None = None
    round_number: int
    round_state: RoundStateResponse
    players: list[PlayerRoundStatus]
    character_questionnaire: CharacterQuestionnaire | None = None
    exposition: Exposition | None = None
    beats: list[Beat] = Field(default_factory=list)
    created_at: datetime


class SubmitActionRequest(BaseModel):
    action_type: Literal["act", "pass"]
    action_text: str | None = None


class ActionResponse(BaseModel):
    accepted: bool
    reason: str | None = None
    game: GameDetailResponse


class AdjudicationError(BaseModel):
    detail: str
    reason: str

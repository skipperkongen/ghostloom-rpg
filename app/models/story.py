"""State models for story state management."""

from uuid import UUID

from pydantic import BaseModel, Field


class Exposition(BaseModel):
    time: str
    place: str
    world_rules: str
    other_characters: list[str]
    relationships: list[str]
    status_quo: str
    backstory: str
    conflict_seed: str
    stakes: str
    tone: str
    genre: str
    theme_hints: list[str]
    inciting_context: str
    rules_of_conflict: list[str]
    foreshadowing: list[str]


class RoundBeatAction(BaseModel):
    character_id: UUID
    character_name: str
    action_type: str
    action_text: str | None = None


class RoundBeat(BaseModel):
    round_number: int
    actions: list[RoundBeatAction] = Field(default_factory=list)
    narrator_text: str


class Story(BaseModel):
    exposition: Exposition
    beats: list[RoundBeat] = Field(default_factory=list)

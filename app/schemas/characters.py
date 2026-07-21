"""Character API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CreateCharacterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=32)
    description: str = Field(min_length=1, max_length=4000)


class UpdateCharacterRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=32)
    description: str | None = Field(default=None, min_length=1, max_length=4000)


class CharacterResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    description: str
    game_id: UUID | None = None
    is_alive: bool
    death_summary: str | None = None
    joined_at: datetime | None = None
    created_at: datetime

"""State models for story state management."""

from typing import Literal
from pydantic import BaseModel, Field

Role = Literal["user", "narrator"]


class Message(BaseModel):
    role: Role
    text: str


class Story(BaseModel):
    seed: str
    messages: list[Message] = Field(default_factory=list)

"""State models for story state management."""

from typing import Literal
from pydantic import BaseModel, Field

Role = Literal["player", "narrator"]


class Exposition(BaseModel):
    # --- Setting ---
    time: str
    place: str
    world_rules: str

    # --- Characters ---
    protagonist: str = Field(
        description="The single player-controlled protagonist, including name and role ",
    )
    other_characters: list[str]
    relationships: list[str]

    # --- Status quo ---
    status_quo: str

    # --- Backstory ---
    backstory: str

    # --- Conflict ---
    conflict_seed: str
    stakes: str

    # --- Tone & structure ---
    tone: str
    genre: str

    # --- Themes ---
    theme_hints: list[str]

    # --- Advanced ---
    inciting_context: str
    rules_of_conflict: list[str]
    foreshadowing: list[str]


class Beat(BaseModel):
    role: Role = Field(description="The role ")
    text: str = Field(description="A description of what happened")


class Story(BaseModel):
    exposition: Exposition = Field(
        description="Establishes the setting, introduces the initial situation and key elements, and hints at direction, stakes, or themes"
    )
    beats: list[Beat] = Field(
        default_factory=list, description="The beats of the story so far"
    )

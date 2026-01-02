from typing import Literal
from pydantic import BaseModel, Field, model_validator

from app.models.story import Story


class InitStoryRequest(BaseModel):
    seed: str


class ContinueStoryRequest(BaseModel):
    story: Story
    user_input: str


class DiceRoll(BaseModel):
    count: int = Field(gt=0)
    faces: int = Field(gt=0)


class Suggestion(BaseModel):
    id: str
    text: str


class StoryResponse(BaseModel):
    story: Story
    next_action: Literal["choose", "roll"]

    suggestions: list[Suggestion] | None = None
    dice_rolls: list[DiceRoll] | None = None

    @model_validator(mode="after")
    def exactly_one_payload(self) -> "StoryResponse":
        has_suggestions = self.suggestions is not None
        has_dice = self.dice_rolls is not None

        if has_suggestions == has_dice:
            raise ValueError(
                "Exactly one of 'suggestions' or 'dice_rolls' must be set."
            )

        if self.next_action == "choose" and not has_suggestions:
            raise ValueError("next_action='choose' requires 'suggestions' to be set.")

        if self.next_action == "roll" and not has_dice:
            raise ValueError("next_action='roll' requires 'dice_rolls' to be set.")

        return self

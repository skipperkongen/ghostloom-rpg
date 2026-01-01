"""Protocol models for API request/response types."""

from pydantic import BaseModel, Field

from app.models.story import Story


class InitStoryRequest(BaseModel):
    seed: str


class ContinueStoryRequest(BaseModel):
    story: Story
    user_input: str


class DiceRoll(BaseModel):
    """Represents a single dice roll specification."""

    count: int = Field(gt=0, description="Number of dice to roll")
    faces: int = Field(
        gt=0, description="Number of faces on each die (e.g., 4, 6, 8, 10, 12, 20, 100)"
    )


class Suggestion(BaseModel):
    id: str
    text: str
    dice_rolls: list[DiceRoll] | None = Field(
        default=None,
        description="Optional list of dice rolls requested for this suggestion. "
        "Each entry specifies a count and number of faces, allowing for "
        "complex combinations like 2d6 + 1d20 in a single request.",
    )


class StoryResponse(BaseModel):
    story: Story
    suggestions: list[Suggestion] | None = None

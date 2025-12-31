"""Protocol models for API request/response types."""

from pydantic import BaseModel

from app.models.story import Story


class InitStoryRequest(BaseModel):
    seed: str


class ContinueStoryRequest(BaseModel):
    story: Story
    user_input: str


class Suggestion(BaseModel):
    id: str
    text: str


class StoryResponse(BaseModel):
    story: Story
    suggestions: list[Suggestion] | None = None

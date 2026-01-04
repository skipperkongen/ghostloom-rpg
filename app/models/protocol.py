from pydantic import BaseModel, Field

from app.models.story import Story


class Choice(BaseModel):
    id: str
    text: str


class InitStoryRequest(BaseModel):
    seed: str


class ContinueStoryRequest(BaseModel):
    story: Story
    user_input: str


class StoryResponse(BaseModel):
    story: Story = Field(description="The full story")
    choices: list[Choice] = Field(
        default_factory=list, description="A list of optional choices"
    )

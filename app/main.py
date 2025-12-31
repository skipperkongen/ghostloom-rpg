"""FastAPI application for the story engine service."""

import os
from fastapi import FastAPI
from pydantic_settings import BaseSettings

from app.models import (
    ContinueStoryRequest,
    InitStoryRequest,
    StoryResponse,
)
from app.narrator import Narrator, SimpleNarrator, suggest_for_input, suggest_for_seed


class Settings(BaseSettings):
    """Application settings from environment variables."""

    llm_api_key: str = os.getenv("LLM_API_KEY", "")

    class Config:
        env_file = ".env"
        case_sensitive = False


# Initialize FastAPI app
app = FastAPI(
    title="Story Engine Service",
    description="A stateless narrative loop service using LLM",
    version="1.0.0",
)


# Global settings and LLM client
settings = Settings()
narrator: Narrator = SimpleNarrator()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/init", response_model=StoryResponse)
def init(req: InitStoryRequest) -> StoryResponse:  # noqa: F821
    story = narrator.init_story(req.seed)
    return StoryResponse(
        story=story,
        suggestions=suggest_for_seed(req.seed),
    )


@app.post("/continue", response_model=StoryResponse)
def continue_(req: ContinueStoryRequest) -> StoryResponse:
    story = narrator.transition(req.story, req.user_input)
    return StoryResponse(
        story=story,
        suggestions=suggest_for_input(req.user_input),
    )

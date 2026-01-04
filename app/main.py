"""FastAPI application for the story engine service."""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings

from app.models import (
    ContinueStoryRequest,
    InitStoryRequest,
    StoryResponse,
)
from app.narrator import Narrator, DummyNarrator


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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins. In production, specify exact origins.
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Global settings and LLM client
settings = Settings()
narrator: Narrator = DummyNarrator()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/init", response_model=StoryResponse)
def init(req: InitStoryRequest) -> StoryResponse:
    story = narrator.initialise_story(req.seed)

    return StoryResponse(story=story)


@app.post("/continue", response_model=StoryResponse)
def continue_(req: ContinueStoryRequest) -> StoryResponse:
    story = narrator.transition(req.story, req.user_input)

    return StoryResponse(story=story)

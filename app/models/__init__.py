"""Pydantic models for request/response types and state management."""

from app.models.protocol import (
    InitStoryRequest,
    ContinueStoryRequest,
    Suggestion,
    StoryResponse,
)
from app.models.story import Role, Message, Story

__all__ = [
    # Protocol models
    "InitStoryRequest",
    "ContinueStoryRequest",
    "Suggestion",
    "StoryResponse",
    # State models
    "Role",
    "Message",
    "Story",
]

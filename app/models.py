"""Pydantic models for request/response types."""

from typing import Any
from pydantic import BaseModel, Field


class InitSessionRequest(BaseModel):
    """Request to initialize a new story session."""

    seed: str = Field(..., description="User's initial story wish or prompt")


class SessionResponse(BaseModel):
    """Response containing session state and narrative text."""

    session_id: str = Field(..., description="Unique session identifier")
    round: int = Field(..., description="Current round number")
    state: str = Field(..., description="Opaque base64-encrypted state token")
    text: str = Field(..., description="Human-readable narrative text")


class StepRequest(BaseModel):
    """Request to take a step in the story."""

    session_id: str = Field(..., description="Session identifier")
    round: int = Field(..., description="Current round number")
    state: str = Field(..., description="Opaque base64-encrypted state token")
    action: str = Field(..., description="User's free-text action")


# Alias for consistency
InitSessionResponse = SessionResponse
StepResponse = SessionResponse


class InternalState(BaseModel):
    """Internal state structure (understood by LLM, not validated strictly)."""

    seed: str
    session_id: str
    round: int
    # Allow additional fields managed by LLM
    extra: dict[str, Any] = Field(default_factory=dict)

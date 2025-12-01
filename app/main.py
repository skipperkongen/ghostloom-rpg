"""FastAPI application for the story engine service."""

import secrets
import os
from fastapi import FastAPI, HTTPException, Depends
from pydantic_settings import BaseSettings

from app.models import (
    InitSessionRequest,
    InitSessionResponse,
    StepRequest,
    StepResponse,
)
from app.crypto import encrypt_state, decrypt_state, get_secret_key
from app.llm_client import LLMClient, StubLLMClient


class Settings(BaseSettings):
    """Application settings from environment variables."""

    state_secret_key: str = os.getenv("STATE_SECRET_KEY", "")
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
llm_client: LLMClient = StubLLMClient()


def get_llm_client() -> LLMClient:
    """Dependency to get LLM client."""
    return llm_client


def get_key() -> bytes:
    """Dependency to get encryption key."""
    try:
        return get_secret_key()
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/session/init", response_model=InitSessionResponse)
async def init_session(
    request: InitSessionRequest,
    client: LLMClient = Depends(get_llm_client),
    secret_key: bytes = Depends(get_key),
):
    """
    Initialize a new story session.

    Creates a new session, generates initial story state using the LLM,
    and returns an encrypted state token.
    """
    try:
        # Generate session ID
        session_id = secrets.token_urlsafe(16)

        # Call LLM to generate initial story
        initial_state_dict, narrative_text = client.init_story(request.seed)

        # Add session_id to state
        initial_state_dict["session_id"] = session_id

        # Encrypt the state
        state_token = encrypt_state(initial_state_dict, secret_key)

        # Return response
        return InitSessionResponse(
            session_id=session_id,
            round=0,
            state=state_token,
            text=narrative_text,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to initialize session: {str(e)}")


@app.post("/session/step", response_model=StepResponse)
async def step_session(
    request: StepRequest,
    client: LLMClient = Depends(get_llm_client),
    secret_key: bytes = Depends(get_key),
):
    """
    Take a step in the story.

    Decrypts the state token, validates it, calls the LLM with the user's action,
    and returns an updated encrypted state token.
    """
    try:
        # Decrypt and verify state
        try:
            decrypted_state = decrypt_state(request.state, secret_key)
        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid or corrupted state token: {str(e)}",
            )

        # Validate session_id matches
        if decrypted_state.get("session_id") != request.session_id:
            raise HTTPException(
                status_code=400,
                detail="Session ID mismatch: state token does not match request",
            )

        # Validate round matches (consistency check)
        decrypted_round = decrypted_state.get("round", -1)
        if decrypted_round != request.round:
            raise HTTPException(
                status_code=400,
                detail=f"Round mismatch: expected {decrypted_round}, got {request.round}",
            )

        # Call LLM to continue story
        updated_state_dict, narrative_text = client.continue_story(
            decrypted_state, request.action
        )

        # Ensure session_id is preserved
        updated_state_dict["session_id"] = request.session_id

        # Encrypt the updated state
        new_state_token = encrypt_state(updated_state_dict, secret_key)

        # Get new round number
        new_round = updated_state_dict.get("round", request.round + 1)

        # Return response
        return StepResponse(
            session_id=request.session_id,
            round=new_round,
            state=new_state_token,
            text=narrative_text,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to process step: {str(e)}")

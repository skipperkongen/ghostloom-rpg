"""FastAPI application for the story engine service."""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings

from app.models import (
    ContinueStoryRequest,
    InitStoryRequest,
    Message,
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
narrator: Narrator = SimpleNarrator()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/init", response_model=StoryResponse)
def init(req: InitStoryRequest) -> StoryResponse:
    story = narrator.init_story(req.seed)
    suggestions, dice_rolls = suggest_for_seed(req.seed)

    if suggestions is not None:
        return StoryResponse(
            story=story,
            next_action="choose",
            suggestions=suggestions,
        )
    else:
        # Adjust narration to mention dice rolling when next_action is "roll"
        if story.messages and dice_rolls:
            last_message = story.messages[-1]
            if last_message.role == "narrator":
                # Format dice notation
                dice_notation = " + ".join(
                    f"{dr.count}d{dr.faces}" for dr in dice_rolls
                )
                # Update the narration to mention dice rolling
                updated_text = last_message.text
                if "What do you do?" in updated_text:
                    updated_text = updated_text.replace(
                        "What do you do?",
                        f"The situation calls for a roll of the dice. Roll {dice_notation} to determine the outcome.\n\nWhat do you do?",
                    )
                else:
                    updated_text += f"\n\nThe situation calls for a roll of the dice. Roll {dice_notation} to determine the outcome."

                # Create a new message list with the updated last message
                updated_messages = story.messages[:-1] + [
                    Message(role=last_message.role, text=updated_text)
                ]
                story = story.model_copy(update={"messages": updated_messages})

        return StoryResponse(
            story=story,
            next_action="roll",
            dice_rolls=dice_rolls,
        )


@app.post("/continue", response_model=StoryResponse)
def continue_(req: ContinueStoryRequest) -> StoryResponse:
    story = narrator.transition(req.story, req.user_input)
    suggestions, dice_rolls = suggest_for_input(req.user_input)

    if suggestions is not None:
        return StoryResponse(
            story=story,
            next_action="choose",
            suggestions=suggestions,
        )
    else:
        # Adjust narration to mention dice rolling when next_action is "roll"
        if story.messages and dice_rolls:
            last_message = story.messages[-1]
            if last_message.role == "narrator":
                # Format dice notation
                dice_notation = " + ".join(
                    f"{dr.count}d{dr.faces}" for dr in dice_rolls
                )
                # Update the narration to mention dice rolling
                updated_text = last_message.text
                if "What do you do next?" in updated_text:
                    updated_text = updated_text.replace(
                        "What do you do next?",
                        f"The situation calls for a roll of the dice. Roll {dice_notation} to determine the outcome.\n\nWhat do you do next?",
                    )
                else:
                    updated_text += f"\n\nThe situation calls for a roll of the dice. Roll {dice_notation} to determine the outcome."

                # Create a new message list with the updated last message
                updated_messages = story.messages[:-1] + [
                    Message(role=last_message.role, text=updated_text)
                ]
                story = story.model_copy(update={"messages": updated_messages})

        return StoryResponse(
            story=story,
            next_action="roll",
            dice_rolls=dice_rolls,
        )

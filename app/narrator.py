"""LLM client abstraction with stub implementation."""

import random
from abc import ABC, abstractmethod

from app.models import Story, Message, Suggestion


class Narrator(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    def init_story(self, seed: str) -> Story:
        """
        Initialize a new story from a seed prompt.

        Args:
            seed: User's initial story wish or prompt

        Returns:
            Narration
        """
        pass

    @abstractmethod
    def transition(self, story: Story, input: str) -> Story:
        """
        Continue the story based on user action.

        Args:
            choice: The player's choice in the story

        Returns:
            Narration
        """
        pass


def make_suggestions(texts: list[str]) -> list[Suggestion]:
    ids = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return [Suggestion(id=ids[i], text=text) for i, text in enumerate(texts)]


# Optional: extremely simple suggestion heuristics.
# Keeps "canon" out of the story transcript.
def suggest_for_seed(seed: str) -> list[Suggestion]:
    # You can make this smarter later; keep it dumb for now.
    return make_suggestions(["Look around", "Move forward", "Call out"])


def suggest_for_input(user_input: str) -> list[Suggestion]:
    # A few generic next moves.
    return make_suggestions(
        ["Proceed cautiously", "Ask a question", "Change my approach"]
    )


class SimpleNarrator(Narrator):
    """
    A minimal, deterministic narrator suitable for testing and scaffolding.
    """

    def init_story(self, seed: str) -> Story:
        random_num = random.randint(1, 9999)
        opening = (
            f"[{random_num}] {seed.strip()}\n\nThe story begins.\n\nWhat do you do?"
        )

        return Story(
            seed=seed,
            messages=[Message(role="narrator", text=opening)],
        )

    def transition(self, story: Story, input: str) -> Story:
        messages = list(story.messages)

        # append user input
        messages.append(Message(role="user", text=input))

        # very simple continuation logic
        random_num = random.randint(1, 9999)
        assistant_text = (
            f"[{random_num}] You decide to {input.strip()}.\n\n"
            "The world responds to your action.\n\n"
            "What do you do next?"
        )

        messages.append(Message(role="narrator", text=assistant_text))

        return Story(
            seed=story.seed,
            messages=messages,
        )

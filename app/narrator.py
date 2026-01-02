"""LLM client abstraction with stub implementation."""

import random
import re
from abc import ABC, abstractmethod

from app.models import Story, Message, Suggestion, DiceRoll


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


def make_dice_suggestion(dice_rolls: list[DiceRoll]) -> list[DiceRoll]:
    """Return dice rolls for the response."""
    return dice_rolls


# Optional: extremely simple suggestion heuristics.
# Keeps "canon" out of the story transcript.
def suggest_for_seed(
    seed: str,
) -> tuple[list[Suggestion] | None, list[DiceRoll] | None]:
    """
    Return either suggestions or dice_rolls, but not both.
    Returns (suggestions, dice_rolls) where exactly one is not None.
    """
    # Sometimes return a dice roll suggestion (30% chance)
    if random.random() < 0.3:
        # Common RPG dice combinations
        dice_options = [
            [DiceRoll(count=1, faces=20)],
            [DiceRoll(count=2, faces=6)],
            [DiceRoll(count=1, faces=20), DiceRoll(count=1, faces=6)],
            [DiceRoll(count=3, faces=6)],
        ]
        dice_rolls = random.choice(dice_options)
        return (None, dice_rolls)

    # Otherwise return normal suggestions
    return (make_suggestions(["Look around", "Move forward", "Call out"]), None)


def suggest_for_input(
    user_input: str,
) -> tuple[list[Suggestion] | None, list[DiceRoll] | None]:
    """
    Return either suggestions or dice_rolls, but not both.
    Returns (suggestions, dice_rolls) where exactly one is not None.
    """
    # If the user just rolled dice, always return suggestions (not more dice rolls)
    if "Rolled:" in user_input:
        return (
            make_suggestions(
                ["Proceed cautiously", "Ask a question", "Change my approach"]
            ),
            None,
        )

    # Sometimes return a dice roll suggestion (30% chance)
    if random.random() < 0.3:
        # Common RPG dice combinations
        dice_options = [
            [DiceRoll(count=1, faces=20)],
            [DiceRoll(count=2, faces=6)],
            [DiceRoll(count=1, faces=20), DiceRoll(count=1, faces=6)],
            [DiceRoll(count=1, faces=100)],
        ]
        dice_rolls = random.choice(dice_options)
        return (None, dice_rolls)

    # Otherwise return normal suggestions
    return (
        make_suggestions(
            ["Proceed cautiously", "Ask a question", "Change my approach"]
        ),
        None,
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

    def _get_dice_roll_context(self, dice_notation: str) -> str:
        """Get contextual text for a dice roll based on the dice notation."""
        # Map dice patterns to context
        if dice_notation == "1d20":
            contexts = [
                "Make a saving throw",
                "Roll for initiative",
                "Make a skill check",
                "Attempt a d20 check",
            ]
        elif dice_notation == "2d6":
            contexts = [
                "Roll for luck",
                "Test your fortune",
                "Roll 2d6",
            ]
        elif dice_notation == "1d20 + 1d6":
            contexts = [
                "Roll for attack and damage",
                "Make an attack roll",
            ]
        elif dice_notation == "3d6":
            contexts = [
                "Roll for ability scores",
                "Roll 3d6",
            ]
        elif dice_notation == "1d100":
            contexts = [
                "Roll percentile dice",
                "Make a percentile check",
            ]
        else:
            contexts = [f"Roll {dice_notation}"]

        return random.choice(contexts)

    def transition(self, story: Story, input: str) -> Story:
        messages = list(story.messages)

        # append user input
        messages.append(Message(role="user", text=input))

        # Check if dice were rolled (look for "Rolled:" pattern)
        dice_rolled = "Rolled:" in input

        # very simple continuation logic
        random_num = random.randint(1, 9999)

        if dice_rolled:
            # Extract dice roll results from the formatted string
            # Format: "1d20 (Rolled: 1d20=15)" or "2d6 (Rolled: 2d6=[3,5]=8, 1d20=[15]=15 (Total: 23))"
            total_match = re.search(r"\(Total: (\d+)\)", input)
            if total_match:
                roll_result = total_match.group(1)
                roll_description = f"a total of {roll_result}"
            else:
                # Try to extract individual roll results
                roll_matches = re.findall(r"=\[?(\d+(?:,\d+)*)\]?=(\d+)", input)
                if roll_matches:
                    # Get the last total from the matches
                    roll_result = roll_matches[-1][1]
                    roll_description = roll_result
                else:
                    # Fallback: extract any number after "Rolled:"
                    simple_match = re.search(r"Rolled:.*?=(\d+)", input)
                    roll_result = simple_match.group(1) if simple_match else "unknown"
                    roll_description = roll_result

            # Extract the dice notation (before the dice roll annotation)
            # Format: "1d20 (Rolled: ...)" -> "1d20"
            dice_notation = re.sub(r"\s*\(Rolled:.*?\)\s*$", "", input).strip()
            if not dice_notation or dice_notation == input:
                # Fallback if regex didn't match
                dice_notation = input.split("(Rolled:")[0].strip()

            # Get contextual text for the dice roll
            context = self._get_dice_roll_context(dice_notation)

            assistant_text = (
                f"[{random_num}] {context}.\n\n"
                f"The dice land showing {roll_description}. The outcome of your roll becomes clear.\n\n"
                "What do you do next?"
            )
        else:
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

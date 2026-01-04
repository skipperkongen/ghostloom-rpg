"""LLM client abstraction with stub implementation."""

from abc import ABC, abstractmethod

from app.models import Beat, Story
from app.models.story import Exposition


class Narrator(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    def generate_exposition(self, seed: str) -> Exposition:
        "Generate a exposition for the story."
        pass

    @abstractmethod
    def generate_narrator_beat(self, story: Story) -> Beat:
        "Generate a narrator beat for the story"
        pass

    @abstractmethod
    def generate_player_beat(self, story: Story, user_input: str) -> Beat:
        "Generate a player beat for the story from user input"
        pass

    def initialise_story(self, seed: str) -> Story:
        """
        Initialize a new story from a seed prompt.

        Args:
            seed: User's initial story wish or prompt

        Returns:
            Story
        """
        story = Story(
            exposition=self.generate_exposition(seed),
            beats=[],
        )
        story.beats.append(self.generate_narrator_beat(story))
        return story

    def transition(self, story: Story, user_input: str) -> Story:
        """
        Continue the story based on user action.
        - Adds two beats (user + narrator)
        Not idempotent, modifies the story

        Args:
            story: The story so far
            input: The player's input or action in the story

        Returns:
            The continued story after processing the user's input, with a user and narrator beat added
        """
        story.beats.append(self.generate_player_beat(story, user_input))
        story.beats.append(self.generate_narrator_beat(story))
        return story


class DummyNarrator(Narrator):
    def generate_exposition(self, seed: str) -> Exposition:
        # A very basic, placeholder exposition using the seed.
        return Exposition(
            protagonist="Alex, an aspiring adventurer",
            time="Present day",
            place=seed if seed else "a mysterious village",
            world_rules="Reality follows everyday logic with a hint of magic.",
            other_characters=["Morgan, a helpful guide"],
            relationships=["Alex and Morgan are friends."],
            status_quo="Alex leads an ordinary life longing for adventure.",
            backstory="Alex has always dreamed of seeing the world beyond the village.",
            conflict_seed="A strange event hints at secrets in the forest.",
            stakes="If Alex investigates, life may change forever.",
            tone="Hopeful and curious",
            genre="Fantasy adventure",
            theme_hints=["Discovery", "Friendship"],
            inciting_context="Rumors have spread about lights in the woods.",
            rules_of_conflict=["Magic is rare but possible."],
            foreshadowing=["Morgan seems to know more than they let on."],
        )

    def generate_narrator_beat(self, story: Story) -> Beat:
        # Very simple canned narration for demonstration.
        narration = (
            f"As the sun rises over {story.exposition.place}, "
            f"{story.exposition.protagonist.split(',')[0]} senses that today will be different."
        )
        return Beat(role="narrator", text=narration)

    def generate_player_beat(self, story: Story, user_input: str) -> Beat:
        # Simply parrots the user_input
        text = f"{story.exposition.protagonist.split(',')[0]} decides to: {user_input}"
        return Beat(role="player", text=text)

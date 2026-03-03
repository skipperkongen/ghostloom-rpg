"""LLM client abstraction with stub implementation."""

import json
from abc import ABC, abstractmethod

from openai import OpenAI

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
        story.beats.append(Beat(role="player", text=user_input))
        story.beats.append(self.generate_narrator_beat(story))
        return story


class DummyNarrator(Narrator):
    def __init__(self, llm_api_key: str):
        self._llm_api_key = llm_api_key
        self._client = OpenAI(api_key=self._llm_api_key) if self._llm_api_key else None

    def generate_exposition(self, seed: str) -> Exposition:
        """Generate an exposition.

        If an LLM API key is configured, use OpenAI for rich exposition.
        Otherwise, fall back to a simple, local exposition so the app
        still works without any external dependencies.
        """
        if not self._client:
            # Offline / no‑LLM fallback
            return Exposition(
                time="An undefined moment in time",
                place="A loosely sketched setting born from your imagination",
                world_rules=(
                    "The world mostly follows common-sense rules, but bends "
                    "whenever it makes the story more interesting."
                ),
                protagonist="You, an inquisitive protagonist exploring this story space",
                other_characters=[
                    "A shifting cast of characters who appear as needed",
                ],
                relationships=[
                    "You feel loosely connected to the people and places you encounter.",
                ],
                status_quo="Life ambles along until your latest idea sparks a new adventure.",
                backstory=(
                    f"Your story begins from a simple idea: '{seed}'. "
                    "Details fill in as you make choices."
                ),
                conflict_seed="Tension emerges whenever you push beyond what is safe or expected.",
                stakes="If you hesitate, the opportunity for discovery may slip away.",
                tone="Curious, flexible, and lightly adventurous.",
                genre="Freeform interactive fiction",
                theme_hints=["Curiosity", "Discovery", "Improvisation"],
                inciting_context="You decide to follow a new thread and see where it leads.",
                rules_of_conflict=[
                    "Consequences follow your choices, but rarely close off all paths.",
                    "The world reacts just enough to keep things interesting.",
                ],
                foreshadowing=[
                    "Unseen possibilities linger just outside your current focus.",
                ],
            )

        system_prompt = (
            "You are a creative storyteller. Generate a detailed story exposition based on the user's seed prompt. "
            "Return your response as a JSON object matching the required structure. "
            "IMPORTANT: All string fields must be plain strings, not objects or lists. "
            "List fields must be arrays of strings."
        )

        user_prompt = (
            f"Generate a story exposition based on this seed prompt: {seed}\n\n"
            "Return a JSON object with the following structure:\n"
            "- time: string (e.g., 'Present day')\n"
            "- place: string (e.g., 'a mysterious village')\n"
            "- world_rules: string (e.g., 'Reality follows everyday logic with a hint of magic.')\n"
            "- protagonist: string (e.g., 'Alex, an aspiring adventurer')\n"
            "- other_characters: array of strings (e.g., ['Morgan, a helpful guide'])\n"
            "- relationships: array of strings (e.g., ['Alex and Morgan are friends.'])\n"
            "- status_quo: string\n"
            "- backstory: string\n"
            "- conflict_seed: string\n"
            "- stakes: string\n"
            "- tone: string\n"
            "- genre: string\n"
            "- theme_hints: array of strings (e.g., ['Discovery', 'Friendship'])\n"
            "- inciting_context: string\n"
            "- rules_of_conflict: array of strings (e.g., ['Magic is rare but possible.'])\n"
            "- foreshadowing: array of strings (e.g., ['Morgan seems to know more than they let on.'])\n\n"
            "All string fields must be plain text strings, not JSON objects or arrays."
        )

        response = self._client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.8,
        )

        response_text = response.choices[0].message.content
        exposition_data = json.loads(response_text)

        # Create Exposition object from the response
        return Exposition(**exposition_data)

    def generate_narrator_beat(self, story: Story) -> Beat:
        """Generate a narrator beat.

        With an API key, this uses OpenAI for narration.
        Without one, it produces a lightweight, local continuation so
        the game loop remains fully playable.
        """
        if not self._client:
            last_player_input = None
            for beat in reversed(story.beats):
                if beat.role == "player":
                    last_player_input = beat.text
                    break

            if last_player_input:
                text = (
                    f"You take a moment to {last_player_input}, and the world subtly "
                    "shifts in response, opening up new possibilities ahead."
                )
            else:
                text = (
                    "The scene settles around you, waiting for your first decisive move."
                )

            return Beat(role="narrator", text=text)

        # Serialize the story to JSON for the prompt
        story_json = story.model_dump_json(indent=2)

        system_prompt = (
            "You are a creative storyteller. Generate a SHORT, CONCISE narrator beat that continues the story. "
            "Return your response as a plain text description (not JSON). "
            "The narration should be written in third person, present tense. "
            "CRITICAL: Keep each beat to 1-2 sentences maximum (20-40 words). "
            "Be direct and to the point - focus on the immediate action or consequence, not lengthy descriptions. "
            "Each beat should advance the story incrementally, leaving room for the player to act."
        )

        user_prompt = (
            f"Given this story context:\n\n{story_json}\n\n"
            f"Generate a SHORT narrator beat (1-2 sentences, 20-40 words max) that continues the story. "
            f"Write in third person, present tense. "
            f"If there was a recent player action, briefly describe the immediate result or consequence. "
            f"Be concise and direct - avoid lengthy descriptions or multiple events. "
            f"Return only the narration text, no JSON, no additional formatting. "
        )

        response = self._client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=100,  # Limit response length to ensure brevity
        )

        beat_text = response.choices[0].message.content.strip()

        return Beat(role="narrator", text=beat_text)

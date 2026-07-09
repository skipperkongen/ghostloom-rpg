"""LLM client abstraction with stub implementation."""

import json
from abc import ABC, abstractmethod

from openai import APIConnectionError, APIStatusError, AuthenticationError, OpenAI, RateLimitError

from app.models import Beat, Story
from app.models.story import Exposition
from app.narrator_types import AcceptedAction, AdjudicationResult, ProgressResult


class Narrator(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    def generate_exposition(self, seed: str, party: list[dict] | None = None) -> Exposition:
        "Generate a exposition for the story."
        pass

    @abstractmethod
    def generate_narrator_beat(self, story: Story) -> Beat:
        "Generate a narrator beat for the story"
        pass

    @abstractmethod
    def adjudicate_action(
        self,
        story: Story,
        exposition: Exposition,
        character: dict,
        action_text: str,
    ) -> AdjudicationResult:
        pass

    @abstractmethod
    def generate_dm_beat(self, story: Story, results: list[AcceptedAction]) -> Beat:
        pass

    @abstractmethod
    def evaluate_progress(self, story: Story, alive_user_ids: list[str]) -> ProgressResult:
        pass

    def initialise_story(self, seed: str, party: list[dict] | None = None) -> Story:
        story = Story(
            exposition=self.generate_exposition(seed, party),
            beats=[],
        )
        story.beats.append(self.generate_narrator_beat(story))
        return story

    def transition(self, story: Story, user_input: str) -> Story:
        story.beats.append(Beat(role="player", text=user_input))
        story.beats.append(self.generate_narrator_beat(story))
        return story


class DummyNarrator(Narrator):
    def __init__(self, llm_api_key: str):
        self._llm_api_key = llm_api_key
        self._client = OpenAI(api_key=self._llm_api_key) if self._llm_api_key else None

    def generate_exposition(self, seed: str, party: list[dict] | None = None) -> Exposition:
        if not self._client:
            party_desc = ""
            if party:
                names = ", ".join(p.get("character_name", "Adventurer") for p in party)
                party_desc = f" The party includes: {names}."
            return Exposition(
                time="An undefined moment in time",
                place="A loosely sketched setting born from your imagination",
                world_rules=(
                    "The world mostly follows common-sense rules, but bends "
                    "whenever it makes the story more interesting."
                ),
                protagonist="A band of adventurers exploring this story space",
                other_characters=[
                    p.get("character_name", "An ally") for p in (party or [])
                ] or ["A shifting cast of characters who appear as needed"],
                relationships=[
                    "The party shares a bond forged by circumstance.",
                ],
                status_quo="Life ambles along until a new adventure sparks.",
                backstory=(
                    f"Your story begins from a simple idea: '{seed}'.{party_desc} "
                    "Details fill in as you make choices."
                ),
                conflict_seed="Tension emerges whenever the party pushes beyond what is safe.",
                stakes="If the party hesitates, opportunity may slip away.",
                tone="Curious, flexible, and lightly adventurous.",
                genre="Freeform interactive fiction",
                theme_hints=["Curiosity", "Discovery", "Cooperation"],
                inciting_context="The party decides to follow a new thread and see where it leads.",
                rules_of_conflict=[
                    "Consequences follow choices, but rarely close off all paths.",
                ],
                foreshadowing=["Unseen possibilities linger just outside focus."],
            )

        party_context = ""
        if party:
            party_context = "\n\nParty members:\n" + "\n".join(
                f"- {p.get('character_name', 'Unknown')}: {p.get('profile', {}).get('summary', 'An adventurer')}"
                for p in party
            )

        system_prompt = (
            "You are a creative storyteller. Generate a detailed story exposition for a multiplayer adventure. "
            "Return JSON matching the required structure. All string fields must be plain strings."
        )
        user_prompt = (
            f"Generate a story exposition based on this seed: {seed}{party_context}\n\n"
            "Return JSON with: time, place, world_rules, protagonist (describe the party), "
            "other_characters (array), relationships (array), status_quo, backstory, conflict_seed, "
            "stakes, tone, genre, theme_hints (array), inciting_context, rules_of_conflict (array), "
            "foreshadowing (array)."
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
        return Exposition(**json.loads(response.choices[0].message.content))

    def generate_narrator_beat(self, story: Story) -> Beat:
        if not self._client:
            last_player_input = None
            for beat in reversed(story.beats):
                if beat.role == "player":
                    last_player_input = beat.text
                    break
            if last_player_input:
                text = (
                    f"The party's actions ripple through the scene as they {last_player_input}, "
                    "opening new possibilities ahead."
                )
            else:
                text = "The scene settles around the party, waiting for their first decisive move."
            return Beat(role="narrator", text=text)

        story_json = story.model_dump_json(indent=2)
        system_prompt = (
            "You are a creative storyteller. Generate a SHORT narrator beat (1-2 sentences, 20-40 words). "
            "Third person, present tense. Plain text only."
        )
        response = self._client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Story context:\n\n{story_json}\n\nGenerate the next narrator beat."},
            ],
            temperature=0.7,
            max_tokens=100,
        )
        return Beat(role="narrator", text=response.choices[0].message.content.strip())

    def adjudicate_action(
        self,
        story: Story,
        exposition: Exposition,
        character: dict,
        action_text: str,
    ) -> AdjudicationResult:
        if not action_text or not action_text.strip():
            return AdjudicationResult(accepted=False, reason="Action text cannot be empty")
        if len(action_text) > 500:
            return AdjudicationResult(accepted=False, reason="Action text is too long (max 500 characters)")

        if not self._client:
            blocked = ["kill everyone", "destroy the world", "god mode"]
            lower = action_text.lower()
            for phrase in blocked:
                if phrase in lower:
                    return AdjudicationResult(accepted=False, reason="That action is not possible in this world")
            return AdjudicationResult(accepted=True)

        system_prompt = (
            "You are a game master adjudicating a player action. "
            'Return JSON: {"accepted": boolean, "reason": string|null}. '
            "Reject actions that break world rules or are impossible. Be fair but consistent."
        )
        user_prompt = (
            f"World rules: {exposition.world_rules}\n"
            f"Character: {character.get('character_name')} - {character.get('profile', {}).get('summary', '')}\n"
            f"Proposed action: {action_text}\n"
            "Should this action be accepted?"
        )
        response = self._client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        data = json.loads(response.choices[0].message.content)
        return AdjudicationResult(accepted=bool(data.get("accepted")), reason=data.get("reason"))

    def generate_dm_beat(self, story: Story, results: list[AcceptedAction]) -> Beat:
        for result in results:
            if result.action_type == "act" and result.action_text:
                story.beats.append(
                    Beat(
                        role="player",
                        text=result.action_text,
                        user_id=str(result.user_id),
                        character_name=result.character_name,
                    )
                )
            elif result.action_type == "pass":
                story.beats.append(
                    Beat(
                        role="player",
                        text=f"{result.character_name} waits and observes.",
                        user_id=str(result.user_id),
                        character_name=result.character_name,
                    )
                )
        return self.generate_narrator_beat(story)

    def evaluate_progress(self, story: Story, alive_user_ids: list[str]) -> ProgressResult:
        if not alive_user_ids:
            return ProgressResult(all_dead=True, arc_phase="end")

        beat_count = len(story.beats)
        if beat_count >= 20:
            return ProgressResult(mission_complete=True, arc_phase="end")
        if beat_count >= 10:
            return ProgressResult(arc_phase="middle")
        return ProgressResult(arc_phase="beginning")


ROUND_RESOLUTION_ERRORS = {
    1001: ("llm_provider_unavailable", "LLM provider is temporarily unavailable or unreachable.", True),
    1002: ("insufficient_credits", "Provider account has insufficient credits or quota.", True),
    1003: ("rate_limited", "Provider rate limit was exceeded.", True),
    1004: ("timeout", "LLM request timed out before completion.", True),
    1005: ("internal_error", "Internal server error during DM resolution.", True),
    1006: ("api_key_not_found", "Game references an API key record that no longer exists.", False),
    1007: ("api_key_not_valid", "Stored API key is rejected by the provider as invalid.", False),
}


def map_openai_error(exc: Exception) -> tuple[int, str, str, bool]:
    if isinstance(exc, AuthenticationError):
        return 1007, *ROUND_RESOLUTION_ERRORS[1007]
    if isinstance(exc, RateLimitError):
        return 1003, *ROUND_RESOLUTION_ERRORS[1003]
    if isinstance(exc, APIConnectionError):
        return 1001, *ROUND_RESOLUTION_ERRORS[1001]
    if isinstance(exc, APIStatusError):
        if exc.status_code == 402:
            return 1002, *ROUND_RESOLUTION_ERRORS[1002]
        if exc.status_code == 429:
            return 1003, *ROUND_RESOLUTION_ERRORS[1003]
    return 1005, *ROUND_RESOLUTION_ERRORS[1005]

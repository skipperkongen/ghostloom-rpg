"""LLM client abstraction with stub implementation."""

import json
from abc import ABC, abstractmethod

from openai import APIConnectionError, APIStatusError, AuthenticationError, OpenAI, RateLimitError

from app.models.story import Exposition, Story
from app.narrator_types import (
    AcceptedAction,
    AdjudicationResult,
    InitStoryResult,
    ProgressResult,
)


def _coerce_to_str(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "; ".join(_coerce_to_str(item) for item in value)
    if isinstance(value, dict):
        char1 = value.get("character1")
        char2 = value.get("character2")
        if char1 and char2:
            detail = value.get("description") or value.get("relationship")
            return f"{char1} and {char2}: {detail}" if detail else f"{char1} and {char2}"

        name = value.get("name") or value.get("character_name")
        detail = value.get("traits") or value.get("trait") or value.get("description")
        parts: list[str] = []
        if name:
            parts.append(str(name))
        if detail:
            if isinstance(detail, list):
                parts.append(", ".join(str(item) for item in detail))
            else:
                parts.append(str(detail))
        if parts:
            return " — ".join(parts)
        return json.dumps(value)
    return str(value)


def _normalize_exposition_data(data: dict) -> dict:
    normalized = dict(data)
    normalized.pop("protagonist", None)
    for field in (
        "time",
        "place",
        "world_rules",
        "status_quo",
        "backstory",
        "conflict_seed",
        "stakes",
        "tone",
        "genre",
        "inciting_context",
    ):
        if field in normalized:
            normalized[field] = _coerce_to_str(normalized[field])
    for field in ("other_characters", "relationships", "theme_hints", "rules_of_conflict", "foreshadowing"):
        if field in normalized and isinstance(normalized[field], list):
            normalized[field] = [_coerce_to_str(item) for item in normalized[field]]
        elif field in normalized:
            normalized[field] = [_coerce_to_str(normalized[field])]
    return normalized


def _party_lines(party: list[dict] | None) -> str:
    if not party:
        return ""
    return "\n\nParty members (player characters — do not invent PCs; put NPCs only in other_characters):\n" + "\n".join(
        f"- {p.get('name', 'Unknown')}: {p.get('description', 'An adventurer')}" for p in party
    )


class Narrator(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    def generate_exposition(self, seed: str, party: list[dict] | None = None) -> Exposition:
        pass

    @abstractmethod
    def generate_narrator_text(self, story: Story) -> str:
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
    def generate_dm_beat(self, story: Story, results: list[AcceptedAction]) -> str:
        pass

    @abstractmethod
    def evaluate_progress(self, story: Story, alive_character_ids: list[str]) -> ProgressResult:
        pass

    def initialise_story(self, seed: str, party: list[dict] | None = None) -> InitStoryResult:
        exposition = self.generate_exposition(seed, party)
        story = Story(exposition=exposition, beats=[])
        narrator_text = self.generate_narrator_text(story)
        return InitStoryResult(exposition=exposition, narrator_text=narrator_text)


class DummyNarrator(Narrator):
    def __init__(self, llm_api_key: str):
        self._llm_api_key = llm_api_key
        self._client = OpenAI(api_key=self._llm_api_key) if self._llm_api_key else None

    def generate_exposition(self, seed: str, party: list[dict] | None = None) -> Exposition:
        if not self._client:
            party_desc = ""
            if party:
                names = ", ".join(p.get("name", "Adventurer") for p in party)
                party_desc = f" The party includes: {names}."
            return Exposition(
                time="An undefined moment in time",
                place="A loosely sketched setting born from your imagination",
                world_rules=(
                    "The world mostly follows common-sense rules, but bends "
                    "whenever it makes the story more interesting."
                ),
                other_characters=["A shifting cast of NPCs who appear as needed"],
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

        party_context = _party_lines(party)
        system_prompt = (
            "You are a creative storyteller. Generate a detailed story exposition for a multiplayer adventure. "
            "Return JSON matching the required structure. "
            "Do not include a protagonist field. Player characters are provided separately; "
            "other_characters must list NPCs only. "
            "other_characters, relationships, theme_hints, rules_of_conflict, and foreshadowing "
            "must be arrays of plain strings, never objects. "
            "You may mention party member names in backstory/stakes using their exact provided names."
        )
        user_prompt = (
            f"Generate a story exposition based on this seed: {seed}{party_context}\n\n"
            "Return JSON with string fields: time, place, world_rules, status_quo, "
            "backstory, conflict_seed, stakes, tone, genre, inciting_context. "
            "Return string arrays for: other_characters, relationships, theme_hints, "
            "rules_of_conflict, foreshadowing."
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
        data = json.loads(response.choices[0].message.content)
        return Exposition(**_normalize_exposition_data(data))

    def generate_narrator_text(self, story: Story) -> str:
        if not self._client:
            last_action_text = None
            for beat in reversed(story.beats):
                for action in reversed(beat.actions):
                    if action.action_type == "act" and action.action_text:
                        last_action_text = action.action_text
                        break
                if last_action_text:
                    break
            if last_action_text:
                return (
                    f"The party's actions ripple through the scene as they {last_action_text}, "
                    "opening new possibilities ahead."
                )
            return "The scene settles around the party, waiting for their first decisive move."

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
        return response.choices[0].message.content.strip()

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
            f"Character: {character.get('name')} - {character.get('description', '')}\n"
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

    def generate_dm_beat(self, story: Story, results: list[AcceptedAction]) -> str:
        # Caller persists actions; temporarily attach for prompt context
        from app.models.story import RoundBeat, RoundBeatAction

        preview = RoundBeat(
            round_number=len(story.beats),
            actions=[
                RoundBeatAction(
                    character_id=r.character_id,
                    character_name=r.character_name,
                    action_type=r.action_type,
                    action_text=r.action_text
                    if r.action_type == "act"
                    else f"{r.character_name} waits and observes.",
                )
                for r in results
            ],
            narrator_text="",
        )
        story_with_actions = Story(exposition=story.exposition, beats=[*story.beats, preview])
        return self.generate_narrator_text(story_with_actions)

    def evaluate_progress(self, story: Story, alive_character_ids: list[str]) -> ProgressResult:
        if not alive_character_ids:
            return ProgressResult(all_dead=True)

        # Round 0 is intro; count completed play rounds
        play_rounds = max(0, len(story.beats) - 1)
        if play_rounds >= 10:
            return ProgressResult(mission_complete=True)
        return ProgressResult()


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

"""Helpers for exposition columns and story beats."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Game, StoryBeat
from app.models.story import Exposition, RoundBeat, RoundBeatAction, Story

EXPOSITION_SCALAR_FIELDS = (
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
)
EXPOSITION_ARRAY_FIELDS = (
    "other_characters",
    "relationships",
    "theme_hints",
    "rules_of_conflict",
    "foreshadowing",
)


def exposition_from_game(game: Game) -> Exposition | None:
    if game.time is None:
        return None
    return Exposition(
        time=game.time or "",
        place=game.place or "",
        world_rules=game.world_rules or "",
        status_quo=game.status_quo or "",
        backstory=game.backstory or "",
        conflict_seed=game.conflict_seed or "",
        stakes=game.stakes or "",
        tone=game.tone or "",
        genre=game.genre or "",
        inciting_context=game.inciting_context or "",
        other_characters=list(game.other_characters or []),
        relationships=list(game.relationships or []),
        theme_hints=list(game.theme_hints or []),
        rules_of_conflict=list(game.rules_of_conflict or []),
        foreshadowing=list(game.foreshadowing or []),
    )


def apply_exposition_to_game(game: Game, exposition: Exposition) -> None:
    for field in EXPOSITION_SCALAR_FIELDS:
        setattr(game, field, getattr(exposition, field))
    for field in EXPOSITION_ARRAY_FIELDS:
        setattr(game, field, list(getattr(exposition, field)))


def round_beats_from_orm(beats: list[StoryBeat]) -> list[RoundBeat]:
    result: list[RoundBeat] = []
    for beat in sorted(beats, key=lambda b: b.round_number):
        result.append(
            RoundBeat(
                round_number=beat.round_number,
                narrator_text=beat.narrator_text,
                actions=[
                    RoundBeatAction(
                        character_id=a.character_id,
                        character_name=a.character_name,
                        action_type=a.action_type.value if hasattr(a.action_type, "value") else str(a.action_type),
                        action_text=a.action_text,
                    )
                    for a in beat.actions
                ],
            )
        )
    return result


def load_story(db: Session, game: Game) -> Story | None:
    exposition = exposition_from_game(game)
    if not exposition:
        return None
    beats = round_beats_from_orm(list(game.story_beats))
    return Story(exposition=exposition, beats=beats)


def current_round_number(db: Session, game_id: UUID) -> int:
    max_round = db.scalar(
        select(func.max(StoryBeat.round_number)).where(StoryBeat.game_id == game_id)
    )
    if max_round is None:
        return 0
    return int(max_round) + 1


def story_beats_load_options():
    return selectinload(Game.story_beats).selectinload(StoryBeat.actions)

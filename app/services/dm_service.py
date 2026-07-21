"""DM round resolution (background task)."""

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from app.db.models import (
    ActionType,
    EndReason,
    Game,
    GamePhase,
    GameStatus,
    PendingAction,
    RoundResolutionFailure,
    StoryBeat,
    StoryBeatAction,
)
from app.db.session import SessionLocal
from app.narrator import ROUND_RESOLUTION_ERRORS
from app.narrator_types import AcceptedAction
from app.services.narrator_service import NarratorCallError, NarratorService
from app.services.phase_service import assert_transition
from app.services.story_loader import current_round_number, load_story, story_beats_load_options


def resolve_dm_round(game_id: str, is_retry: bool = False) -> None:
    db = SessionLocal()
    try:
        game = db.scalar(
            select(Game)
            .where(Game.id == UUID(game_id))
            .options(
                selectinload(Game.runtime),
                selectinload(Game.characters),
                selectinload(Game.pending_actions),
                story_beats_load_options(),
            )
            .with_for_update()
        )
        if not game or not game.runtime:
            return
        if game.runtime.phase not in (GamePhase.dm_round, GamePhase.resolution_failed):
            return

        round_number = current_round_number(db, game.id)
        narrator_service = NarratorService(db)

        try:
            story = load_story(db, game)
            if not story:
                raise RuntimeError("Game story not initialized")
            results = _build_accepted_actions(game)

            def run_dm(narrator):
                narrator_text = narrator.generate_dm_beat(story, results)
                beat = StoryBeat(
                    game_id=game.id,
                    round_number=round_number,
                    narrator_text=narrator_text,
                )
                db.add(beat)
                db.flush()
                for result in results:
                    action_type = (
                        ActionType.pass_ if result.action_type == "pass" else ActionType.act
                    )
                    db.add(
                        StoryBeatAction(
                            story_beat_id=beat.id,
                            character_id=result.character_id,
                            character_name=result.character_name,
                            action_type=action_type,
                            action_text=result.action_text,
                        )
                    )
                db.flush()
                db.expire(game, ["story_beats"])
                story_after = load_story(db, game)
                assert story_after is not None

                alive_ids = [
                    str(c.id) for c in game.characters if c.game_id == game.id and c.is_alive
                ]
                progress = narrator.evaluate_progress(story_after, alive_ids)

                for death in progress.deaths:
                    character = next(
                        (c for c in game.characters if str(c.id) == str(death.character_id)),
                        None,
                    )
                    if character and character.is_alive:
                        character.is_alive = False
                        character.death_summary = death.death_summary

                alive = [c for c in game.characters if c.game_id == game.id and c.is_alive]
                if progress.all_dead or not alive:
                    assert_transition(game.runtime.phase, GamePhase.ended)
                    _end_and_release(game, EndReason.all_dead)
                elif progress.mission_complete:
                    assert_transition(game.runtime.phase, GamePhase.ended)
                    _end_and_release(game, EndReason.mission_complete)
                else:
                    assert_transition(game.runtime.phase, GamePhase.player_round)
                    game.runtime.phase = GamePhase.player_round
                    db.execute(delete(PendingAction).where(PendingAction.game_id == game.id))

            narrator_service.run_with_narrator(game, run_dm)
            db.commit()
        except NarratorCallError as exc:
            db.rollback()
            game = db.scalar(
                select(Game)
                .where(Game.id == UUID(game_id))
                .options(
                    selectinload(Game.runtime),
                    selectinload(Game.resolution_failures),
                )
                .with_for_update()
            )
            if not game:
                return
            error_name, _, retryable = ROUND_RESOLUTION_ERRORS.get(
                exc.error_code, ("internal_error", exc.message, True)
            )
            attempt = 1
            if is_retry:
                latest = (
                    max(game.resolution_failures, key=lambda f: f.failed_at)
                    if game.resolution_failures
                    else None
                )
                attempt = (latest.attempt_count + 1) if latest else 1

            failure = RoundResolutionFailure(
                game_id=game.id,
                round_number=round_number,
                error_code=exc.error_code,
                error_code_name=error_name,
                error_message=exc.message,
                retryable=exc.retryable if hasattr(exc, "retryable") else retryable,
                attempt_count=attempt,
            )
            game.runtime.phase = GamePhase.resolution_failed
            db.add(failure)
            db.commit()
        except Exception as exc:
            db.rollback()
            game = db.scalar(
                select(Game)
                .where(Game.id == UUID(game_id))
                .options(selectinload(Game.runtime))
                .with_for_update()
            )
            if not game:
                return
            failure = RoundResolutionFailure(
                game_id=game.id,
                round_number=round_number,
                error_code=1005,
                error_code_name="internal_error",
                error_message=str(exc),
                retryable=True,
                attempt_count=1,
            )
            game.runtime.phase = GamePhase.resolution_failed
            db.add(failure)
            db.commit()
    finally:
        db.close()


def _end_and_release(game: Game, end_reason: EndReason) -> None:
    game.runtime.status = GameStatus.ended
    game.runtime.phase = GamePhase.ended
    game.runtime.end_reason = end_reason
    for character in list(game.characters):
        if character.game_id == game.id:
            character.game_id = None
            character.joined_at = None


def _build_accepted_actions(game: Game) -> list[AcceptedAction]:
    results: list[AcceptedAction] = []
    for action in game.pending_actions:
        character = next((c for c in game.characters if c.id == action.character_id), None)
        if not character:
            continue
        results.append(
            AcceptedAction(
                character_id=character.id,
                character_name=character.name,
                action_type=action.action_type.value,
                action_text=action.action_text,
            )
        )
    return results

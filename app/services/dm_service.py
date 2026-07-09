"""DM round resolution (background task)."""

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from app.db.models import (
    ArcPhase,
    EndReason,
    Game,
    GamePhase,
    GameStatus,
    PendingAction,
    RoundResolutionFailure,
)
from app.db.session import SessionLocal
from app.models.story import Story
from app.narrator import ROUND_RESOLUTION_ERRORS
from app.narrator_types import AcceptedAction
from app.services.narrator_service import NarratorCallError, NarratorService
from app.services.phase_service import assert_transition


def resolve_dm_round(game_id: str, is_retry: bool = False) -> None:
    db = SessionLocal()
    try:
        game = db.scalar(
            select(Game)
            .where(Game.id == UUID(game_id))
            .options(
                selectinload(Game.players),
                selectinload(Game.pending_actions),
            )
            .with_for_update()
        )
        if not game:
            return
        if game.phase not in (GamePhase.dm_round, GamePhase.resolution_failed):
            return

        round_number = game.round_number
        narrator_service = NarratorService(db)

        try:
            story = Story(**game.story_data) if game.story_data else Story(
                exposition=game.exposition, beats=[]
            )
            results = _build_accepted_actions(game)

            def run_dm(narrator):
                beat = narrator.generate_dm_beat(story, results)
                story.beats.append(beat)
                alive_ids = [str(p.user_id) for p in game.players if p.is_alive]
                progress = narrator.evaluate_progress(story, alive_ids)

                for death in progress.deaths:
                    player = next((p for p in game.players if str(p.user_id) == death.user_id), None)
                    if player and player.is_alive:
                        player.is_alive = False
                        player.death_round = game.round_number
                        player.death_summary = death.death_summary

                game.arc_phase = ArcPhase(progress.arc_phase)
                game.story_data = story.model_dump()

                alive = [p for p in game.players if p.is_alive]
                if progress.all_dead or not alive:
                    assert_transition(game.phase, GamePhase.ended)
                    game.status = GameStatus.ended
                    game.phase = GamePhase.ended
                    game.end_reason = EndReason.all_dead
                elif progress.mission_complete:
                    assert_transition(game.phase, GamePhase.ended)
                    game.status = GameStatus.ended
                    game.phase = GamePhase.ended
                    game.end_reason = EndReason.mission_complete
                else:
                    assert_transition(game.phase, GamePhase.player_round)
                    game.phase = GamePhase.player_round
                    game.round_number += 1
                    db.execute(delete(PendingAction).where(PendingAction.game_id == game.id))

            narrator_service.run_with_narrator(game, run_dm)
            db.commit()
        except NarratorCallError as exc:
            db.rollback()
            game = db.scalar(
                select(Game)
                .where(Game.id == UUID(game_id))
                .options(selectinload(Game.resolution_failures))
                .with_for_update()
            )
            if not game:
                return
            error_name, _, retryable = ROUND_RESOLUTION_ERRORS.get(
                exc.error_code, ("internal_error", exc.message, True)
            )
            attempt = 1
            if is_retry:
                latest = max(game.resolution_failures, key=lambda f: f.failed_at) if game.resolution_failures else None
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
            game.phase = GamePhase.resolution_failed
            db.add(failure)
            db.commit()
        except Exception as exc:
            db.rollback()
            game = db.scalar(select(Game).where(Game.id == UUID(game_id)).with_for_update())
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
            game.phase = GamePhase.resolution_failed
            db.add(failure)
            db.commit()
    finally:
        db.close()


def _build_accepted_actions(game: Game) -> list[AcceptedAction]:
    results: list[AcceptedAction] = []
    for action in game.pending_actions:
        player = next((p for p in game.players if p.user_id == action.user_id), None)
        if not player:
            continue
        results.append(
            AcceptedAction(
                user_id=action.user_id,
                character_name=player.character_name or "Unknown",
                action_type=action.action_type.value,
                action_text=action.action_text,
            )
        )
    return results

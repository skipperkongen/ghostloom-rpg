"""Player turn and action handling."""

from uuid import UUID

from fastapi import BackgroundTasks
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ActionType, Game, GamePhase, PendingAction
from app.models.story import Exposition, Story
from app.schemas.games import ActionResponse
from app.services.dm_service import resolve_dm_round
from app.services.game_service import GameError, GameService
from app.services.narrator_service import NarratorService
from app.services.phase_service import ENDPOINT_PHASES, assert_phase_allowed


class TurnService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.game_service = GameService(db)
        self.narrator_service = NarratorService(db)

    def submit_action(
        self,
        game_id: UUID,
        user_id: UUID,
        action_type: str,
        action_text: str | None,
        background_tasks: BackgroundTasks,
    ) -> ActionResponse:
        game = self.game_service.get_game_for_user(game_id, user_id)
        self.game_service.assert_not_ended(game)
        assert_phase_allowed(game.phase, ENDPOINT_PHASES["actions"], "actions")

        player = self.game_service._get_player(game, user_id)
        if not player or not player.is_alive:
            raise GameError("Only alive players can submit actions", 403)

        if action_type == "act":
            if not action_text or not action_text.strip():
                raise GameError("action_text is required for act", 400)
            story = Story(**game.story_data) if game.story_data else None
            exposition = Exposition(**game.exposition) if game.exposition else None
            if not story or not exposition:
                raise GameError("Game story not initialized", 500)

            character = {
                "character_name": player.character_name,
                "profile": (player.character_description or {}).get("profile", {}),
            }

            def adjudicate(narrator):
                return narrator.adjudicate_action(story, exposition, character, action_text.strip())

            result = self.narrator_service.run_with_narrator(game, adjudicate)
            if not result.accepted:
                game_detail = self.game_service.to_detail(game, user_id)
                return ActionResponse(accepted=False, reason=result.reason, game=game_detail)

            self._upsert_pending_action(game, user_id, ActionType.act, action_text.strip())
        elif action_type == "pass":
            self._upsert_pending_action(game, user_id, ActionType.pass_, None)
        else:
            raise GameError("action_type must be 'act' or 'pass'", 400)

        self.db.commit()
        game = self.game_service._load_game(game_id)

        if self._all_alive_submitted(game):
            game.phase = GamePhase.dm_round
            self.db.commit()
            background_tasks.add_task(resolve_dm_round, str(game.id))

        game = self.game_service._load_game(game_id)
        return ActionResponse(
            accepted=True,
            game=self.game_service.to_detail(game, user_id),
        )

    def _upsert_pending_action(
        self,
        game: Game,
        user_id: UUID,
        action_type: ActionType,
        action_text: str | None,
    ) -> None:
        existing = self.db.scalar(
            select(PendingAction).where(
                PendingAction.game_id == game.id,
                PendingAction.user_id == user_id,
            )
        )
        if existing:
            existing.action_type = action_type
            existing.action_text = action_text
        else:
            self.db.add(
                PendingAction(
                    game_id=game.id,
                    user_id=user_id,
                    action_type=action_type,
                    action_text=action_text,
                )
            )

    def _all_alive_submitted(self, game: Game) -> bool:
        alive_ids = {p.user_id for p in game.players if p.is_alive}
        submitted_ids = {a.user_id for a in game.pending_actions}
        return alive_ids and alive_ids <= submitted_ids

"""Game business logic."""

import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.character_templates import (
    build_character_profile,
    get_questionnaire_for_seed,
    validate_answers,
)
from app.db.models import (
    ArcPhase,
    EndReason,
    Game,
    GamePhase,
    GamePlayer,
    GameStatus,
    RoundResolutionFailure,
    User,
)
from app.models.story import Beat, Story
from app.schemas.games import (
    GameDetailResponse,
    GameSummaryResponse,
    PlayerRoundStatus,
    RoundStateResponse,
)
from app.services.api_key_service import ApiKeyService
from app.services.narrator_service import NarratorService
from app.services.phase_service import ENDPOINT_PHASES, assert_phase_allowed

MAX_PLAYERS = 5
CHARACTER_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9 \-]{0,30}[a-zA-Z0-9]$|^[a-zA-Z0-9]$")


class GameError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class GameService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.api_key_service = ApiKeyService(db)
        self.narrator_service = NarratorService(db)

    def create_game(self, user: User, seed: str, api_key_id: UUID) -> Game:
        self.api_key_service.get_owned_key(user.id, api_key_id)
        game = Game(
            host_user_id=user.id,
            seed=seed.strip(),
            api_key_id=api_key_id,
            status=GameStatus.lobby,
            phase=GamePhase.lobby,
            arc_phase=ArcPhase.beginning,
            round_number=0,
        )
        self.db.add(game)
        self.db.flush()
        self.db.add(GamePlayer(game_id=game.id, user_id=user.id))
        self.db.commit()
        return self._load_game(game.id)

    def list_games(self, user_id: UUID) -> list[Game]:
        return list(
            self.db.scalars(
                select(Game)
                .join(GamePlayer, GamePlayer.game_id == Game.id)
                .where(GamePlayer.user_id == user_id)
                .order_by(Game.created_at.desc())
            )
        )

    def get_game_for_user(self, game_id: UUID, user_id: UUID) -> Game:
        game = self._load_game(game_id)
        if not self._is_member(game, user_id):
            raise GameError("Not a member of this game", 403)
        return game

    def join_game(self, game_id: UUID, user: User) -> Game:
        game = self._load_game(game_id)
        assert_phase_allowed(game.phase, ENDPOINT_PHASES["join"], "join")
        if game.status != GameStatus.lobby:
            raise GameError("Cannot join: game has already started", 409)
        if self._is_member(game, user.id):
            raise GameError("Already a member of this game", 409)
        alive_count = len(game.players)
        if alive_count >= MAX_PLAYERS:
            raise GameError("Game is full (max 5 players)", 409)
        self.db.add(GamePlayer(game_id=game.id, user_id=user.id))
        self.db.commit()
        return self._load_game(game.id)

    def leave_game(self, game_id: UUID, user: User) -> Game:
        game = self.get_game_for_user(game_id, user.id)
        assert_phase_allowed(game.phase, ENDPOINT_PHASES["leave"], "leave")
        player = self._get_player(game, user.id)
        if not player:
            raise GameError("Not a member of this game", 403)

        if game.phase == GamePhase.lobby:
            self.db.delete(player)
            if game.host_user_id == user.id:
                remaining = [p for p in game.players if p.user_id != user.id]
                if remaining:
                    game.host_user_id = remaining[0].user_id
                else:
                    game.status = GameStatus.ended
                    game.phase = GamePhase.ended
        else:
            player.is_alive = False
            player.death_round = game.round_number
            player.death_summary = "Player left the game"
            if game.host_user_id == user.id:
                self._transfer_host(game, exclude_user_id=user.id)
            self._check_all_dead(game)

        self.db.commit()
        return self._load_game(game.id)

    def update_character(
        self,
        game_id: UUID,
        user: User,
        character_name: str,
        answers: list[dict],
    ) -> Game:
        game = self.get_game_for_user(game_id, user.id)
        assert_phase_allowed(game.phase, ENDPOINT_PHASES["update_character"], "update_character")
        player = self._get_player(game, user.id)
        if not player:
            raise GameError("Not a member of this game", 403)

        name = character_name.strip()
        if not CHARACTER_NAME_PATTERN.match(name):
            raise GameError(
                "Character name must be 1-32 characters, alphanumeric with spaces/hyphens"
            )
        answer_errors = validate_answers(answers)
        if answer_errors:
            raise GameError("; ".join(answer_errors))

        profile = build_character_profile(answers)
        questionnaire_complete = len(answers) >= len(get_questionnaire_for_seed(game.seed).questions)
        player.character_name = name
        player.character_description = {
            "answers": answers,
            "profile": profile,
            "questionnaire_complete": questionnaire_complete,
        }
        self.db.commit()
        return self._load_game(game.id)

    def start_game(self, game_id: UUID, user: User) -> Game:
        game = self.get_game_for_user(game_id, user.id)
        assert_phase_allowed(game.phase, ENDPOINT_PHASES["start"], "start")
        if game.host_user_id != user.id:
            raise GameError("Only the host can start the game", 403)
        if len(game.players) < 1:
            raise GameError("At least one player is required", 400)
        for player in game.players:
            desc = player.character_description or {}
            if not player.character_name or not desc.get("questionnaire_complete"):
                raise GameError("All players must complete character creation before starting")

        party = [
            {
                "character_name": p.character_name,
                "profile": (p.character_description or {}).get("profile", {}),
            }
            for p in game.players
        ]

        def run(narrator):
            return narrator.initialise_story(game.seed, party)

        story = self.narrator_service.run_with_narrator(game, run)
        game.exposition = story.exposition.model_dump()
        game.story_data = story.model_dump()
        game.status = GameStatus.active
        game.phase = GamePhase.player_round
        game.arc_phase = ArcPhase.beginning
        game.round_number = 1
        self.db.commit()
        return self._load_game(game.id)

    def to_summary(self, game: Game) -> GameSummaryResponse:
        return GameSummaryResponse(
            id=game.id,
            seed=game.seed,
            status=game.status.value,
            phase=game.phase.value,
            host_user_id=game.host_user_id,
            round_number=game.round_number,
            created_at=game.created_at,
        )

    def to_detail(self, game: Game, current_user_id: UUID | None = None) -> GameDetailResponse:
        pending_user_ids = {a.user_id for a in game.pending_actions}
        latest_failure = self._latest_failure(game)

        players: list[PlayerRoundStatus] = []
        for player in game.players:
            user = self.db.get(User, player.user_id)
            desc = player.character_description or {}
            players.append(
                PlayerRoundStatus(
                    user_id=player.user_id,
                    display_name=user.display_name if user else None,
                    character_name=player.character_name,
                    is_alive=player.is_alive,
                    life_state="alive" if player.is_alive else "dead",
                    death_round=player.death_round,
                    death_summary=player.death_summary,
                    action_submitted=player.user_id in pending_user_ids,
                    questionnaire_complete=bool(desc.get("questionnaire_complete")),
                )
            )

        round_state = self._build_round_state(game, latest_failure)
        exposition = None
        beats: list[Beat] = []
        if game.exposition:
            from app.models.story import Exposition

            exposition = Exposition(**game.exposition)
        if game.story_data:
            story = Story(**game.story_data)
            beats = story.beats

        questionnaire = None
        if game.phase == GamePhase.lobby:
            questionnaire = get_questionnaire_for_seed(game.seed)

        return GameDetailResponse(
            id=game.id,
            seed=game.seed,
            status=game.status.value,
            phase=game.phase.value,
            host_user_id=game.host_user_id,
            arc_phase=game.arc_phase.value,
            end_reason=game.end_reason.value if game.end_reason else None,
            round_number=game.round_number,
            round_state=round_state,
            players=players,
            character_questionnaire=questionnaire,
            exposition=exposition,
            beats=beats,
            created_at=game.created_at,
        )

    def assert_not_ended(self, game: Game) -> None:
        if game.phase == GamePhase.ended or game.status == GameStatus.ended:
            raise GameError("Game has ended and is read-only", 409)

    def _build_round_state(self, game: Game, failure: RoundResolutionFailure | None) -> RoundStateResponse:
        if game.phase == GamePhase.player_round:
            return RoundStateResponse(status="actions_pending")
        if game.phase == GamePhase.dm_round:
            return RoundStateResponse(status="resolving_round")
        if game.phase == GamePhase.resolution_failed and failure:
            return RoundStateResponse(
                status="resolution_failed",
                error_code=failure.error_code,
                error_code_name=failure.error_code_name,
                error_message=failure.error_message,
                retryable=failure.retryable,
                attempt_count=failure.attempt_count,
            )
        if game.phase == GamePhase.ended:
            return RoundStateResponse(status="resolved")
        return RoundStateResponse(status="resolved")

    def _latest_failure(self, game: Game) -> RoundResolutionFailure | None:
        if not game.resolution_failures:
            return None
        return max(game.resolution_failures, key=lambda f: f.failed_at)

    def _load_game(self, game_id: UUID) -> Game:
        game = self.db.scalar(
            select(Game)
            .where(Game.id == game_id)
            .options(
                selectinload(Game.players),
                selectinload(Game.pending_actions),
                selectinload(Game.resolution_failures),
            )
        )
        if not game:
            raise GameError("Game not found", 404)
        return game

    def _is_member(self, game: Game, user_id: UUID) -> bool:
        return any(p.user_id == user_id for p in game.players)

    def _get_player(self, game: Game, user_id: UUID) -> GamePlayer | None:
        return next((p for p in game.players if p.user_id == user_id), None)

    def _transfer_host(self, game: Game, exclude_user_id: UUID) -> None:
        candidates = sorted(
            [p for p in game.players if p.user_id != exclude_user_id and p.is_alive],
            key=lambda p: p.joined_at,
        )
        if candidates:
            game.host_user_id = candidates[0].user_id
        else:
            game.status = GameStatus.ended
            game.phase = GamePhase.ended
            game.end_reason = EndReason.all_dead

    def _check_all_dead(self, game: Game) -> None:
        alive = [p for p in game.players if p.is_alive]
        if not alive:
            game.status = GameStatus.ended
            game.phase = GamePhase.ended
            game.end_reason = EndReason.all_dead

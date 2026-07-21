"""Game business logic."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import (
    Character,
    EndReason,
    Game,
    GamePhase,
    GameRuntime,
    GameStatus,
    RoundResolutionFailure,
    StoryBeat,
    User,
)
from app.schemas.games import (
    GameDetailResponse,
    GameSummaryResponse,
    PlayerRoundStatus,
    RoundStateResponse,
)
from app.services.api_key_service import ApiKeyService
from app.services.character_service import CharacterService
from app.services.narrator_service import NarratorService
from app.services.phase_service import ENDPOINT_PHASES, assert_phase_allowed
from app.services.story_loader import (
    apply_exposition_to_game,
    current_round_number,
    exposition_from_game,
    round_beats_from_orm,
    story_beats_load_options,
)

MAX_PLAYERS = 5


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
        self.character_service = CharacterService(db)

    def create_game(self, user: User, seed: str, api_key_id: UUID, character_id: UUID) -> Game:
        self.api_key_service.get_owned_key(user.id, api_key_id)
        character = self.character_service.get_owned(character_id, user.id)
        self._assert_character_joinable(character)

        game = Game(
            host_user_id=user.id,
            seed=seed.strip(),
            api_key_id=api_key_id,
        )
        self.db.add(game)
        self.db.flush()
        self.db.add(
            GameRuntime(
                game_id=game.id,
                status=GameStatus.lobby,
                phase=GamePhase.lobby,
            )
        )
        self._assign_character_to_game(character, game.id)
        self.db.commit()
        return self._load_game(game.id)

    def list_games(self, user_id: UUID) -> list[Game]:
        return list(
            self.db.scalars(
                select(Game)
                .outerjoin(Character, Character.game_id == Game.id)
                .where(or_(Game.host_user_id == user_id, Character.user_id == user_id))
                .options(selectinload(Game.runtime))
                .order_by(Game.created_at.desc())
                .distinct()
            )
        )

    def get_game_for_user(self, game_id: UUID, user_id: UUID) -> Game:
        game = self._load_game(game_id)
        if not self._can_access(game, user_id):
            raise GameError("Not a member of this game", 403)
        return game

    def join_game(self, game_id: UUID, user: User, character_id: UUID) -> Game:
        game = self._load_game(game_id)
        assert_phase_allowed(game.runtime.phase, ENDPOINT_PHASES["join"], "join")
        if game.runtime.status != GameStatus.lobby:
            raise GameError("Cannot join: game has already started", 409)
        if self._user_in_cast(game, user.id):
            raise GameError("Already a member of this game", 409)
        if len(game.characters) >= MAX_PLAYERS:
            raise GameError("Game is full (max 5 players)", 409)

        character = self.character_service.get_owned(character_id, user.id)
        self._assert_character_joinable(character)
        self._assign_character_to_game(character, game.id)
        self.db.commit()
        return self._load_game(game.id)

    def leave_game(self, game_id: UUID, user: User) -> Game:
        game = self.get_game_for_user(game_id, user.id)
        assert_phase_allowed(game.runtime.phase, ENDPOINT_PHASES["leave"], "leave")
        character = self._get_character_for_user(game, user.id)
        if not character:
            raise GameError("Not a member of this game", 403)

        pending = next((a for a in game.pending_actions if a.character_id == character.id), None)
        if pending:
            self.db.delete(pending)

        self._clear_character_game(character)

        if game.runtime.phase == GamePhase.lobby:
            if game.host_user_id == user.id:
                remaining = [c for c in game.characters if c.game_id == game.id]
                if remaining:
                    game.host_user_id = remaining[0].user_id
                else:
                    self._end_game(game, end_reason=None)
        else:
            if game.host_user_id == user.id:
                self._transfer_host(game, exclude_user_id=user.id)
            self._check_all_dead(game)

        self.db.commit()
        return self._load_game(game.id)

    def start_game(self, game_id: UUID, user: User) -> Game:
        game = self.get_game_for_user(game_id, user.id)
        assert_phase_allowed(game.runtime.phase, ENDPOINT_PHASES["start"], "start")
        if game.host_user_id != user.id:
            raise GameError("Only the host can start the game", 403)
        cast = [c for c in game.characters if c.game_id == game.id]
        if len(cast) < 1:
            raise GameError("At least one player is required", 400)

        party = [{"name": c.name, "description": c.description} for c in cast]

        def run(narrator):
            return narrator.initialise_story(game.seed, party)

        result = self.narrator_service.run_with_narrator(game, run)
        apply_exposition_to_game(game, result.exposition)
        self.db.add(
            StoryBeat(
                game_id=game.id,
                round_number=0,
                narrator_text=result.narrator_text,
            )
        )
        game.runtime.status = GameStatus.active
        game.runtime.phase = GamePhase.player_round
        self.db.commit()
        return self._load_game(game.id)

    def to_summary(self, game: Game) -> GameSummaryResponse:
        return GameSummaryResponse(
            id=game.id,
            seed=game.seed,
            status=game.runtime.status.value,
            phase=game.runtime.phase.value,
            host_user_id=game.host_user_id,
            round_number=current_round_number(self.db, game.id),
            created_at=game.created_at,
        )

    def to_detail(self, game: Game, current_user_id: UUID | None = None) -> GameDetailResponse:
        pending_ids = {a.character_id for a in game.pending_actions}
        latest_failure = self._latest_failure(game)
        cast = sorted(
            [c for c in game.characters if c.game_id == game.id],
            key=lambda c: c.joined_at or c.created_at,
        )

        players: list[PlayerRoundStatus] = []
        for character in cast:
            user = self.db.get(User, character.user_id)
            players.append(
                PlayerRoundStatus(
                    character_id=character.id,
                    user_id=character.user_id,
                    display_name=user.display_name if user else None,
                    name=character.name,
                    description=character.description,
                    is_alive=character.is_alive,
                    life_state="alive" if character.is_alive else "dead",
                    death_summary=character.death_summary,
                    action_submitted=character.id in pending_ids,
                )
            )

        return GameDetailResponse(
            id=game.id,
            seed=game.seed,
            status=game.runtime.status.value,
            phase=game.runtime.phase.value,
            host_user_id=game.host_user_id,
            end_reason=game.runtime.end_reason.value if game.runtime.end_reason else None,
            round_number=current_round_number(self.db, game.id),
            round_state=self._build_round_state(game, latest_failure),
            players=players,
            exposition=exposition_from_game(game),
            beats=round_beats_from_orm(list(game.story_beats)),
            created_at=game.created_at,
        )

    def assert_not_ended(self, game: Game) -> None:
        if game.runtime.phase == GamePhase.ended or game.runtime.status == GameStatus.ended:
            raise GameError("Game has ended and is read-only", 409)

    def end_game_and_release_cast(self, game: Game, end_reason: EndReason | None) -> None:
        self._end_game(game, end_reason)

    def _end_game(self, game: Game, end_reason: EndReason | None) -> None:
        game.runtime.status = GameStatus.ended
        game.runtime.phase = GamePhase.ended
        game.runtime.end_reason = end_reason
        for character in list(game.characters):
            if character.game_id == game.id:
                self._clear_character_game(character)

    def _build_round_state(self, game: Game, failure: RoundResolutionFailure | None) -> RoundStateResponse:
        phase = game.runtime.phase
        if phase == GamePhase.player_round:
            return RoundStateResponse(status="actions_pending")
        if phase == GamePhase.dm_round:
            return RoundStateResponse(status="resolving_round")
        if phase == GamePhase.resolution_failed and failure:
            return RoundStateResponse(
                status="resolution_failed",
                error_code=failure.error_code,
                error_code_name=failure.error_code_name,
                error_message=failure.error_message,
                retryable=failure.retryable,
                attempt_count=failure.attempt_count,
            )
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
                selectinload(Game.runtime),
                selectinload(Game.characters),
                selectinload(Game.pending_actions),
                selectinload(Game.resolution_failures),
                story_beats_load_options(),
            )
        )
        if not game:
            raise GameError("Game not found", 404)
        return game

    def _can_access(self, game: Game, user_id: UUID) -> bool:
        if game.host_user_id == user_id:
            return True
        return self._user_in_cast(game, user_id)

    def _user_in_cast(self, game: Game, user_id: UUID) -> bool:
        return any(c.user_id == user_id and c.game_id == game.id for c in game.characters)

    def _get_character_for_user(self, game: Game, user_id: UUID) -> Character | None:
        return next((c for c in game.characters if c.user_id == user_id and c.game_id == game.id), None)

    def _assert_character_joinable(self, character: Character) -> None:
        if not character.is_alive:
            raise GameError("Dead characters cannot join games", 409)
        if character.game_id is not None:
            raise GameError("Character is already in a game", 409)

    def _assign_character_to_game(self, character: Character, game_id: UUID) -> None:
        character.game_id = game_id
        character.joined_at = datetime.now(timezone.utc)

    def _clear_character_game(self, character: Character) -> None:
        character.game_id = None
        character.joined_at = None

    def _transfer_host(self, game: Game, exclude_user_id: UUID) -> None:
        candidates = sorted(
            [
                c
                for c in game.characters
                if c.game_id == game.id and c.user_id != exclude_user_id and c.is_alive
            ],
            key=lambda c: c.joined_at or c.created_at,
        )
        if candidates:
            game.host_user_id = candidates[0].user_id
        else:
            self._end_game(game, EndReason.all_dead)

    def _check_all_dead(self, game: Game) -> None:
        alive = [c for c in game.characters if c.game_id == game.id and c.is_alive]
        if not alive:
            self._end_game(game, EndReason.all_dead)

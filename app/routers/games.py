"""Games router."""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.session import get_db
from app.dependencies import get_current_user
from app.schemas.games import (
    ActionResponse,
    CreateGameRequest,
    GameDetailResponse,
    GameSummaryResponse,
    SubmitActionRequest,
    UpdateCharacterRequest,
)
from app.services.dm_service import resolve_dm_round
from app.services.game_service import GameError, GameService
from app.services.phase_service import PhaseError
from app.services.turn_service import TurnService

router = APIRouter(prefix="/games", tags=["games"])


def _handle_game_error(exc: GameError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.message)


@router.post("", response_model=GameDetailResponse, status_code=201)
def create_game(
    req: CreateGameRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GameDetailResponse:
    service = GameService(db)
    try:
        game = service.create_game(user, req.seed, req.api_key_id)
    except Exception as exc:
        from app.services.api_key_service import ApiKeyError

        if isinstance(exc, ApiKeyError):
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        raise
    return service.to_detail(game, user.id)


@router.get("", response_model=list[GameSummaryResponse])
def list_games(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[GameSummaryResponse]:
    service = GameService(db)
    return [service.to_summary(g) for g in service.list_games(user.id)]


@router.get("/{game_id}", response_model=GameDetailResponse)
def get_game(
    game_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GameDetailResponse:
    service = GameService(db)
    try:
        game = service.get_game_for_user(game_id, user.id)
    except GameError as exc:
        raise _handle_game_error(exc) from exc
    return service.to_detail(game, user.id)


@router.post("/{game_id}/join", response_model=GameDetailResponse)
def join_game(
    game_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GameDetailResponse:
    service = GameService(db)
    try:
        game = service.join_game(game_id, user)
    except (GameError, PhaseError) as exc:
        status_code = exc.status_code if isinstance(exc, GameError) else 409
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    return service.to_detail(game, user.id)


@router.post("/{game_id}/leave", response_model=GameDetailResponse)
def leave_game(
    game_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GameDetailResponse:
    service = GameService(db)
    try:
        game = service.leave_game(game_id, user)
    except (GameError, PhaseError) as exc:
        status_code = exc.status_code if isinstance(exc, GameError) else 409
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    return service.to_detail(game, user.id)


@router.patch("/{game_id}/players/me", response_model=GameDetailResponse)
def update_character(
    game_id: UUID,
    req: UpdateCharacterRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GameDetailResponse:
    service = GameService(db)
    answers = [a.model_dump() for a in req.answers]
    try:
        game = service.update_character(game_id, user, req.character_name, answers)
    except (GameError, PhaseError) as exc:
        status_code = exc.status_code if isinstance(exc, GameError) else 409
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    return service.to_detail(game, user.id)


@router.post("/{game_id}/start", response_model=GameDetailResponse)
def start_game(
    game_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GameDetailResponse:
    service = GameService(db)
    try:
        game = service.start_game(game_id, user)
    except (GameError, PhaseError) as exc:
        status_code = exc.status_code if isinstance(exc, GameError) else 409
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    except Exception as exc:
        from app.services.narrator_service import NarratorCallError

        if isinstance(exc, NarratorCallError):
            raise HTTPException(status_code=502, detail=exc.message) from exc
        raise
    return service.to_detail(game, user.id)


@router.post("/{game_id}/actions", response_model=ActionResponse)
def submit_action(
    game_id: UUID,
    req: SubmitActionRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ActionResponse:
    service = TurnService(db)
    try:
        return service.submit_action(
            game_id, user.id, req.action_type, req.action_text, background_tasks
        )
    except (GameError, PhaseError) as exc:
        status_code = exc.status_code if isinstance(exc, GameError) else 409
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.post("/{game_id}/retry-resolution", response_model=GameDetailResponse)
def retry_game_resolution(
    game_id: UUID,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GameDetailResponse:
    from app.db.models import GamePhase
    from app.services.phase_service import ENDPOINT_PHASES, assert_phase_allowed

    service = GameService(db)
    try:
        game = service.get_game_for_user(game_id, user.id)
        if game.host_user_id != user.id:
            raise GameError("Only the host can retry resolution", 403)
        assert_phase_allowed(game.phase, ENDPOINT_PHASES["retry_resolution"], "retry_resolution")
        game.phase = GamePhase.dm_round
        db.commit()
        background_tasks.add_task(resolve_dm_round, str(game.id), True)
        game = service._load_game(game_id)
    except (GameError, PhaseError) as exc:
        status_code = exc.status_code if isinstance(exc, GameError) else 409
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    return service.to_detail(game, user.id)

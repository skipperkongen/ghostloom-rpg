"""Characters router."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.session import get_db
from app.dependencies import get_current_user
from app.schemas.characters import (
    CharacterResponse,
    CreateCharacterRequest,
    UpdateCharacterRequest,
)
from app.services.character_service import CharacterError, CharacterService

router = APIRouter(prefix="/characters", tags=["characters"])


def _handle(exc: CharacterError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.message)


@router.post("", response_model=CharacterResponse, status_code=201)
def create_character(
    req: CreateCharacterRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CharacterResponse:
    service = CharacterService(db)
    try:
        character = service.create(user, req.name, req.description)
    except CharacterError as exc:
        raise _handle(exc) from exc
    return service.to_response(character)


@router.get("", response_model=list[CharacterResponse])
def list_characters(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CharacterResponse]:
    service = CharacterService(db)
    return [service.to_response(c) for c in service.list_for_user(user.id)]


@router.get("/{character_id}", response_model=CharacterResponse)
def get_character(
    character_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CharacterResponse:
    service = CharacterService(db)
    try:
        character = service.get_owned(character_id, user.id)
    except CharacterError as exc:
        raise _handle(exc) from exc
    return service.to_response(character)


@router.patch("/{character_id}", response_model=CharacterResponse)
def update_character(
    character_id: UUID,
    req: UpdateCharacterRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CharacterResponse:
    service = CharacterService(db)
    try:
        character = service.update(character_id, user.id, req.name, req.description)
    except CharacterError as exc:
        raise _handle(exc) from exc
    return service.to_response(character)


@router.delete("/{character_id}", status_code=204)
def delete_character(
    character_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    service = CharacterService(db)
    try:
        service.delete(character_id, user.id)
    except CharacterError as exc:
        raise _handle(exc) from exc

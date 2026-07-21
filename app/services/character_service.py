"""Character CRUD service."""

import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Character, User
from app.schemas.characters import CharacterResponse

CHARACTER_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9 \-]{0,30}[a-zA-Z0-9]$|^[a-zA-Z0-9]$")


class CharacterError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class CharacterService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, user: User, name: str, description: str) -> Character:
        clean_name = self._validate_name(name)
        clean_desc = self._validate_description(description)
        character = Character(
            user_id=user.id,
            name=clean_name,
            description=clean_desc,
            is_alive=True,
        )
        self.db.add(character)
        self.db.commit()
        self.db.refresh(character)
        return character

    def list_for_user(self, user_id: UUID) -> list[Character]:
        return list(
            self.db.scalars(
                select(Character)
                .where(Character.user_id == user_id)
                .order_by(Character.created_at.desc())
            )
        )

    def get_owned(self, character_id: UUID, user_id: UUID) -> Character:
        character = self.db.get(Character, character_id)
        if not character or character.user_id != user_id:
            raise CharacterError("Character not found", 404)
        return character

    def update(
        self,
        character_id: UUID,
        user_id: UUID,
        name: str | None,
        description: str | None,
    ) -> Character:
        character = self.get_owned(character_id, user_id)
        if character.game_id is not None:
            raise CharacterError("Cannot edit a character while they are in a game", 409)
        if name is not None:
            character.name = self._validate_name(name)
        if description is not None:
            character.description = self._validate_description(description)
        self.db.commit()
        self.db.refresh(character)
        return character

    def delete(self, character_id: UUID, user_id: UUID) -> None:
        character = self.get_owned(character_id, user_id)
        if character.game_id is not None:
            raise CharacterError("Cannot delete a character while they are in a game", 409)
        self.db.delete(character)
        self.db.commit()

    def to_response(self, character: Character) -> CharacterResponse:
        return CharacterResponse(
            id=character.id,
            user_id=character.user_id,
            name=character.name,
            description=character.description,
            game_id=character.game_id,
            is_alive=character.is_alive,
            death_summary=character.death_summary,
            joined_at=character.joined_at,
            created_at=character.created_at,
        )

    def _validate_name(self, name: str) -> str:
        clean = name.strip()
        if not CHARACTER_NAME_PATTERN.match(clean):
            raise CharacterError(
                "Character name must be 1-32 characters, alphanumeric with spaces/hyphens"
            )
        return clean

    def _validate_description(self, description: str) -> str:
        clean = description.strip()
        if not clean or len(clean) > 4000:
            raise CharacterError("Character description must be 1-4000 characters")
        return clean

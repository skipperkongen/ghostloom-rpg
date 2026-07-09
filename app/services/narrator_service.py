"""Narrator factory with BYOK key loading."""


from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import ApiKey, Game
from app.narrator import DummyNarrator, Narrator, map_openai_error
from app.services.api_key_service import ApiKeyService


class NarratorService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.api_key_service = ApiKeyService(db)

    def get_narrator_for_game(self, game: Game) -> Narrator:
        api_key = self.db.get(ApiKey, game.api_key_id)
        if not api_key:
            raise KeyError("api_key_not_found")
        try:
            plaintext = self.api_key_service.decrypt_key(api_key)
        except ValueError as exc:
            raise KeyError("api_key_not_valid") from exc
        if not plaintext and settings.llm_api_key:
            return DummyNarrator(llm_api_key=settings.llm_api_key)
        return DummyNarrator(llm_api_key=plaintext)

    def run_with_narrator(self, game: Game, fn):
        try:
            narrator = self.get_narrator_for_game(game)
            return fn(narrator)
        except KeyError as exc:
            code = 1006 if str(exc) == "api_key_not_found" else 1007
            raise NarratorCallError(code, str(exc)) from exc
        except Exception as exc:
            code, name, message, retryable = map_openai_error(exc)
            raise NarratorCallError(code, message, retryable=retryable) from exc


class NarratorCallError(Exception):
    def __init__(self, error_code: int, message: str, retryable: bool = True) -> None:
        self.error_code = error_code
        self.message = message
        self.retryable = retryable
        super().__init__(message)

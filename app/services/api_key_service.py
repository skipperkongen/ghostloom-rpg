"""API key management service."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ApiKey, ApiKeyVendor
from app.services.crypto_service import CryptoService


class ApiKeyError(Exception):
    pass


class ApiKeyService:
    def __init__(self, db: Session, crypto: CryptoService | None = None) -> None:
        self.db = db
        self.crypto = crypto or CryptoService()

    def list_keys(self, user_id: UUID) -> list[ApiKey]:
        return list(self.db.scalars(select(ApiKey).where(ApiKey.user_id == user_id).order_by(ApiKey.created_at)))

    def create_key(self, user_id: UUID, vendor: str, plaintext_key: str) -> ApiKey:
        if vendor != "openai":
            raise ApiKeyError("Only openai vendor is supported in v1")
        if len(plaintext_key) < 4:
            raise ApiKeyError("API key is too short")

        encrypted = self.crypto.encrypt(plaintext_key)
        api_key = ApiKey(
            user_id=user_id,
            vendor=ApiKeyVendor.openai,
            api_key=encrypted,
            last_four=plaintext_key[-4:],
        )
        self.db.add(api_key)
        self.db.commit()
        self.db.refresh(api_key)
        return api_key

    def delete_key(self, user_id: UUID, key_id: UUID) -> None:
        api_key = self.db.scalar(
            select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user_id)
        )
        if not api_key:
            raise ApiKeyError("API key not found")
        self.db.delete(api_key)
        self.db.commit()

    def get_owned_key(self, user_id: UUID, key_id: UUID) -> ApiKey:
        api_key = self.db.scalar(
            select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user_id)
        )
        if not api_key:
            raise ApiKeyError("API key not found")
        return api_key

    def decrypt_key(self, api_key: ApiKey) -> str:
        return self.crypto.decrypt(api_key.api_key)

"""Fernet encryption for BYOK API keys."""

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


class CryptoService:
    def __init__(self, encryption_key: str | None = None) -> None:
        key = encryption_key or settings.byok_encryption_key
        if not key:
            raise ValueError("BYOK_ENCRYPTION_KEY is required")
        self._fernet = Fernet(key.encode() if isinstance(key, str) else key)

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except InvalidToken as exc:
            raise ValueError("Failed to decrypt API key") from exc


def generate_encryption_key() -> str:
    return Fernet.generate_key().decode()

"""Authentication service."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import bcrypt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import Session as UserSession
from app.db.models import User


class AuthError(Exception):
    pass


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def register(self, email: str, password: str, display_name: str) -> tuple[User, str, datetime]:
        existing = self.db.scalar(select(User).where(User.email == email.lower()))
        if existing:
            raise AuthError("Email already registered")

        user = User(
            email=email.lower(),
            password_hash=self._hash_password(password),
            display_name=display_name.strip(),
        )
        self.db.add(user)
        self.db.flush()
        token, expires_at = self._create_session(user.id)
        self.db.commit()
        self.db.refresh(user)
        return user, token, expires_at

    def login(self, email: str, password: str) -> tuple[User, str, datetime]:
        user = self.db.scalar(select(User).where(User.email == email.lower()))
        if not user or not self._verify_password(password, user.password_hash):
            raise AuthError("Invalid email or password")
        token, expires_at = self._create_session(user.id)
        self.db.commit()
        return user, token, expires_at

    def logout(self, token: str) -> None:
        token_hash = self._hash_token(token)
        session = self.db.scalar(select(UserSession).where(UserSession.token_hash == token_hash))
        if session:
            self.db.delete(session)
            self.db.commit()

    def get_user_by_token(self, token: str) -> User | None:
        token_hash = self._hash_token(token)
        session = self.db.scalar(select(UserSession).where(UserSession.token_hash == token_hash))
        if not session:
            return None
        if session.expires_at < datetime.now(UTC):
            self.db.delete(session)
            self.db.commit()
            return None
        return self.db.get(User, session.user_id)

    def _create_session(self, user_id: UUID) -> tuple[str, datetime]:
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(UTC) + timedelta(days=settings.session_ttl_days)
        session = UserSession(
            user_id=user_id,
            token_hash=self._hash_token(token),
            expires_at=expires_at,
        )
        self.db.add(session)
        return token, expires_at

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def _hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    @staticmethod
    def _verify_password(password: str, password_hash: str) -> bool:
        return bcrypt.checkpw(password.encode(), password_hash.encode())

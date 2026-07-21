"""SQLAlchemy ORM models."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ApiKeyVendor(str, enum.Enum):
    openai = "openai"


class GameStatus(str, enum.Enum):
    lobby = "lobby"
    active = "active"
    ended = "ended"


class GamePhase(str, enum.Enum):
    lobby = "lobby"
    player_round = "player_round"
    dm_round = "dm_round"
    resolution_failed = "resolution_failed"
    ended = "ended"


class EndReason(str, enum.Enum):
    all_dead = "all_dead"
    mission_complete = "mission_complete"


class ActionType(str, enum.Enum):
    act = "act"
    pass_ = "pass"


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    return [e.value for e in enum_cls]


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    sessions: Mapped[list["Session"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    api_keys: Mapped[list["ApiKey"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    characters: Mapped[list["Character"]] = relationship(back_populates="user")


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="sessions")


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    vendor: Mapped[ApiKeyVendor] = mapped_column(Enum(ApiKeyVendor, values_callable=_enum_values), nullable=False)
    api_key: Mapped[str] = mapped_column(Text, nullable=False)
    last_four: Mapped[str] = mapped_column(String(4), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="api_keys")
    games: Mapped[list["Game"]] = relationship(back_populates="api_key")


class Game(Base):
    __tablename__ = "games"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    host_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    seed: Mapped[str] = mapped_column(Text, nullable=False)
    api_key_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    time: Mapped[str | None] = mapped_column(Text, nullable=True)
    place: Mapped[str | None] = mapped_column(Text, nullable=True)
    world_rules: Mapped[str | None] = mapped_column(Text, nullable=True)
    status_quo: Mapped[str | None] = mapped_column(Text, nullable=True)
    backstory: Mapped[str | None] = mapped_column(Text, nullable=True)
    conflict_seed: Mapped[str | None] = mapped_column(Text, nullable=True)
    stakes: Mapped[str | None] = mapped_column(Text, nullable=True)
    tone: Mapped[str | None] = mapped_column(Text, nullable=True)
    genre: Mapped[str | None] = mapped_column(Text, nullable=True)
    inciting_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    other_characters: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    relationships: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    theme_hints: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    rules_of_conflict: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    foreshadowing: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)

    api_key: Mapped["ApiKey"] = relationship(back_populates="games")
    runtime: Mapped["GameRuntime"] = relationship(
        back_populates="game", uselist=False, cascade="all, delete-orphan"
    )
    characters: Mapped[list["Character"]] = relationship(
        back_populates="game", order_by="Character.joined_at"
    )
    story_beats: Mapped[list["StoryBeat"]] = relationship(
        back_populates="game", cascade="all, delete-orphan", order_by="StoryBeat.round_number"
    )
    pending_actions: Mapped[list["PendingAction"]] = relationship(
        back_populates="game", cascade="all, delete-orphan"
    )
    resolution_failures: Mapped[list["RoundResolutionFailure"]] = relationship(
        back_populates="game", cascade="all, delete-orphan"
    )


class GameRuntime(Base):
    __tablename__ = "game_runtime"

    game_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("games.id"), primary_key=True
    )
    status: Mapped[GameStatus] = mapped_column(
        Enum(GameStatus, values_callable=_enum_values), nullable=False, default=GameStatus.lobby
    )
    phase: Mapped[GamePhase] = mapped_column(
        Enum(GamePhase, values_callable=_enum_values), nullable=False, default=GamePhase.lobby
    )
    end_reason: Mapped[EndReason | None] = mapped_column(
        Enum(EndReason, values_callable=_enum_values), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    game: Mapped["Game"] = relationship(back_populates="runtime")


class Character(Base):
    __tablename__ = "characters"
    __table_args__ = (
        Index(
            "uq_characters_game_user",
            "game_id",
            "user_id",
            unique=True,
            postgresql_where=text("game_id IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    game_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("games.id"), nullable=True, index=True
    )
    is_alive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    death_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="characters")
    game: Mapped["Game | None"] = relationship(back_populates="characters")


class StoryBeat(Base):
    __tablename__ = "story_beats"
    __table_args__ = (UniqueConstraint("game_id", "round_number", name="uq_story_beats_game_round"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    game_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("games.id"), nullable=False, index=True)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    narrator_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    game: Mapped["Game"] = relationship(back_populates="story_beats")
    actions: Mapped[list["StoryBeatAction"]] = relationship(
        back_populates="story_beat", cascade="all, delete-orphan"
    )


class StoryBeatAction(Base):
    __tablename__ = "story_beat_actions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    story_beat_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("story_beats.id"), nullable=False, index=True
    )
    character_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("characters.id"), nullable=False
    )
    character_name: Mapped[str] = mapped_column(String(32), nullable=False)
    action_type: Mapped[ActionType] = mapped_column(Enum(ActionType, values_callable=_enum_values), nullable=False)
    action_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    story_beat: Mapped["StoryBeat"] = relationship(back_populates="actions")


class PendingAction(Base):
    __tablename__ = "pending_actions"
    __table_args__ = (UniqueConstraint("game_id", "character_id", name="uq_pending_actions_game_character"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    game_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("games.id"), nullable=False, index=True)
    character_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("characters.id"), nullable=False)
    action_type: Mapped[ActionType] = mapped_column(Enum(ActionType, values_callable=_enum_values), nullable=False)
    action_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    game: Mapped["Game"] = relationship(back_populates="pending_actions")


class RoundResolutionFailure(Base):
    __tablename__ = "round_resolution_failures"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    game_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("games.id"), nullable=False, index=True)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    error_code: Mapped[int] = mapped_column(Integer, nullable=False)
    error_code_name: Mapped[str] = mapped_column(String(64), nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    retryable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    failed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    game: Mapped["Game"] = relationship(back_populates="resolution_failures")

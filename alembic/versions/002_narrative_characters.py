"""narrative storage and reusable characters

Revision ID: 002
Revises: 001
Create Date: 2026-07-20

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EXPOSITION_TEXT_COLS = (
    "time",
    "place",
    "world_rules",
    "status_quo",
    "backstory",
    "conflict_seed",
    "stakes",
    "tone",
    "genre",
    "inciting_context",
)
EXPOSITION_ARRAY_COLS = (
    "other_characters",
    "relationships",
    "theme_hints",
    "rules_of_conflict",
    "foreshadowing",
)


def upgrade() -> None:
    for col in EXPOSITION_TEXT_COLS:
        op.add_column("games", sa.Column(col, sa.Text(), nullable=True))
    for col in EXPOSITION_ARRAY_COLS:
        op.add_column("games", sa.Column(col, postgresql.ARRAY(sa.Text()), nullable=True))

    gamestatus = postgresql.ENUM(
        "lobby", "active", "ended", name="gamestatus", create_type=False
    )
    gamephase = postgresql.ENUM(
        "lobby",
        "player_round",
        "dm_round",
        "resolution_failed",
        "ended",
        name="gamephase",
        create_type=False,
    )
    endreason = postgresql.ENUM(
        "all_dead", "mission_complete", name="endreason", create_type=False
    )
    actiontype = postgresql.ENUM("act", "pass", name="actiontype", create_type=False)

    op.create_table(
        "game_runtime",
        sa.Column("game_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", gamestatus, nullable=False),
        sa.Column("phase", gamephase, nullable=False),
        sa.Column("end_reason", endreason, nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"]),
        sa.PrimaryKeyConstraint("game_id"),
    )

    op.execute(
        """
        INSERT INTO game_runtime (game_id, status, phase, end_reason, updated_at)
        SELECT id, status, phase, end_reason, COALESCE(updated_at, now())
        FROM games
        """
    )

    op.create_table(
        "characters",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("game_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_alive", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("death_summary", sa.Text(), nullable=True),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_characters_user_id"), "characters", ["user_id"], unique=False)
    op.create_index(op.f("ix_characters_game_id"), "characters", ["game_id"], unique=False)
    op.create_index(
        "uq_characters_game_user",
        "characters",
        ["game_id", "user_id"],
        unique=True,
        postgresql_where=sa.text("game_id IS NOT NULL"),
    )

    op.create_table(
        "story_beats",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("game_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("narrator_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("game_id", "round_number", name="uq_story_beats_game_round"),
    )
    op.create_index(op.f("ix_story_beats_game_id"), "story_beats", ["game_id"], unique=False)

    op.create_table(
        "story_beat_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("story_beat_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("character_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("character_name", sa.String(length=32), nullable=False),
        sa.Column("action_type", actiontype, nullable=False),
        sa.Column("action_text", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["character_id"], ["characters.id"]),
        sa.ForeignKeyConstraint(["story_beat_id"], ["story_beats.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_story_beat_actions_story_beat_id"), "story_beat_actions", ["story_beat_id"], unique=False)

    op.drop_constraint("uq_pending_actions_game_user", "pending_actions", type_="unique")
    op.add_column("pending_actions", sa.Column("character_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.execute("DELETE FROM pending_actions")
    op.alter_column("pending_actions", "character_id", nullable=False)
    op.create_foreign_key(
        "fk_pending_actions_character_id",
        "pending_actions",
        "characters",
        ["character_id"],
        ["id"],
    )
    op.create_unique_constraint("uq_pending_actions_game_character", "pending_actions", ["game_id", "character_id"])
    op.drop_column("pending_actions", "user_id")

    op.drop_index(op.f("ix_game_players_user_id"), table_name="game_players")
    op.drop_index(op.f("ix_game_players_game_id"), table_name="game_players")
    op.drop_table("game_players")

    op.drop_column("games", "updated_at")
    op.drop_column("games", "round_number")
    op.drop_column("games", "story_data")
    op.drop_column("games", "exposition")
    op.drop_column("games", "end_reason")
    op.drop_column("games", "arc_phase")
    op.drop_column("games", "phase")
    op.drop_column("games", "status")

    op.execute("DROP TYPE IF EXISTS arcphase")


def downgrade() -> None:
    raise NotImplementedError("Downgrade from 002 is not supported")

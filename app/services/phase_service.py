"""Game phase transition rules."""

from app.db.models import GamePhase

PHASE_TRANSITIONS: dict[GamePhase, set[GamePhase]] = {
    GamePhase.lobby: {GamePhase.player_round, GamePhase.ended},
    GamePhase.player_round: {GamePhase.dm_round, GamePhase.ended},
    GamePhase.dm_round: {GamePhase.player_round, GamePhase.resolution_failed, GamePhase.ended},
    GamePhase.resolution_failed: {GamePhase.dm_round, GamePhase.ended},
    GamePhase.ended: set(),
}

ENDPOINT_PHASES: dict[str, set[GamePhase]] = {
    "join": {GamePhase.lobby},
    "leave": {
        GamePhase.lobby,
        GamePhase.player_round,
        GamePhase.dm_round,
        GamePhase.resolution_failed,
    },
    "update_character": {GamePhase.lobby},
    "start": {GamePhase.lobby},
    "actions": {GamePhase.player_round},
    "retry_resolution": {GamePhase.resolution_failed},
}


class PhaseError(Exception):
    pass


def assert_phase_allowed(current: GamePhase, allowed: set[GamePhase], action: str) -> None:
    if current not in allowed:
        raise PhaseError(f"Action '{action}' is not allowed in phase '{current.value}'")


def assert_transition(current: GamePhase, next_phase: GamePhase) -> None:
    allowed = PHASE_TRANSITIONS.get(current, set())
    if next_phase not in allowed:
        raise PhaseError(f"Cannot transition from '{current.value}' to '{next_phase.value}'")

# Big Change

Replace the stateless single-player story API with a **client-agnostic FastAPI service backed by PostgreSQL**. The server is the source of truth for users, games, and turns. Clients authenticate with bearer tokens and call a clean REST API.

## Goals

### Multiplayer turns

- **Player round:** every alive player submits one action or passes.
- **DM round:** when all alive players have acted, the server adjudicates actions and advances the world. The DM may reject choices that are unrealistic for the setting and explain why.
- Rejected actions do not become player beats.

### Characters

- Players join a game in a lobby phase, claim a character, and customise name and description before play starts.

### Story arc

- Enforce a narrative arc with **beginning**, **middle**, and **end** phases.
- The DM tracks arc progression each round.

### End conditions

- Game ends if **all players die** — dead players can no longer act.
- Game ends if the **story arc reaches the end** (mission accomplished).
- Ended games are read-only.

### Bring your own API key (BYOK)

- Remove the server-wide `OPENAI_API_KEY` as the default way to play.
- Each user may store an OpenAI API key once on their profile.
- The server wraps the key with a symmetric server secret (AES-256-GCM) and persists only the ciphertext in the database.
- The server never returns the plaintext or wrapped key to the client — only `{ "api_key_configured": true, "api_key_hint": "...x7Qa" }` (last four characters).
- On each LLM call the server unwraps the **host’s** key in memory, calls the API, and discards the plaintext.
- Users do not re-enter their key for every new game.
- Creating or starting a game requires the host to have a key configured.

### Export and import

- Export produces a versioned JSON snapshot of a game (story, players, arc, round state).
- Export **never** includes API keys or session tokens.
- Import creates a new game from a snapshot; the importer becomes host.

## Architecture

```text
Client (any)  ──Bearer token──►  FastAPI  ──►  PostgreSQL
                                    │
                                    └── Narrator (LLM, per-request host key)
```

- **Routers** are thin; **services** enforce game rules, membership, phases, and key presence.
- Reuse existing narrative types (`Exposition`, `Beat`, `Story`) inside game state (JSONB).
- Deprecate and remove the stateless `POST /init` and `POST /continue` loop once the new API is in place.

## Authentication

Generic session auth — no provider-specific routes in the core API.

```http
POST /auth/register   { "email", "password", "display_name" }
POST /auth/login      { "email", "password" }
POST /auth/logout     Authorization: Bearer …
```

All other routes require `Authorization: Bearer <access_token>`. The core resolves `user_id` from the token and does not care which client obtained it.

External identity providers (OAuth, bots, etc.) can be added later by minting the same session token; the game API stays unchanged.

## API surface

### Profile and settings

```http
GET    /me
GET    /me/settings
PUT    /me/settings/api-key      # plaintext in, never out
DELETE /me/settings/api-key
```

### Games

```http
POST   /games
GET    /games
GET    /games/{game_id}
POST   /games/{game_id}/join
POST   /games/{game_id}/leave
PATCH  /games/{game_id}/players/me    # claim / customise character
POST   /games/{game_id}/start         # host only; runs exposition, opens round 1
POST   /games/{game_id}/actions       # act or pass during player round
GET    /games/{game_id}/export
POST   /games/import
```

### Health

```http
GET /health
```

## Game lifecycle

```text
lobby → active → ended
         │
         └── player_round ⇄ dm_round (repeat until ended)
```

| Phase | Behaviour |
|-------|-----------|
| `lobby` | Join, leave, customise character; host starts when ready |
| `player_round` | Each alive player submits one action or pass |
| `dm_round` | Server adjudicates, narrates, updates arc; triggered when all alive players have acted |
| `ended` | Read-only; reason is `all_dead` or `mission_complete` |

When the last alive player acts in a round, the server runs the DM step synchronously and returns the updated game state.

## Database (minimal)

```text
users
  id, email, password_hash, display_name
  wrapped_api_key, api_key_hint
  created_at, updated_at

sessions
  id, user_id, token_hash, expires_at, created_at

games
  id, host_user_id, seed
  status       — lobby | active | ended
  phase        — lobby | player_round | dm_round | ended
  arc_phase    — beginning | middle | end
  end_reason   — null | all_dead | mission_complete
  exposition   — JSONB
  story_data   — JSONB (beats, world state)
  round_number
  created_at, updated_at

game_players
  game_id, user_id
  character_name, character_description
  is_alive
  joined_at

pending_actions          # current player round only
  id, game_id, user_id
  action_type              — act | pass
  action_text
  adjudication             — null | accepted | rejected
  rejection_reason
  created_at
```

## Narrator changes

Extend the existing `Narrator` abstraction:

- `adjudicate_actions(story, actions)` — accept or reject each action with a reason
- `generate_dm_beat(story, results)` — narrate the round
- `evaluate_progress(story)` — update arc phase, deaths, mission complete

## Export format

```json
{
  "format": "ghostloom-game",
  "version": 1,
  "exported_at": "…",
  "game": {
    "seed": "…",
    "exposition": { },
    "story_data": { },
    "arc_phase": "middle",
    "round_number": 4,
    "players": [ ],
    "status": "active",
    "phase": "player_round"
  }
}
```

## Deployment

The API ships as a **Docker image** and is deployed to a container host (e.g. Coolify).

- One image runs the FastAPI app; PostgreSQL is a separate service (managed DB or container).
- Configuration via environment variables (database URL, session secret, key-encryption secret, CORS origins).
- **Cross-origin clients** must be allowed: the API may live on a subdomain (e.g. `api.ghostloom.com`) while clients run on other domains or subdomains (e.g. `ghostloom.com`, `ghostloomgame.com`).
- CORS is configured explicitly — allowed origins come from env (not `*` in production) and include credentials/headers needed for bearer auth.

## CI/CD

On every push to **`main`**, GitHub Actions builds the Docker image and publishes it to **GitHub Container Registry (GHCR)**.

- Image tag: commit SHA; also tag `latest` on main.
- Package name: `ghcr.io/<org>/ghostloom-api` (or equivalent org/repo naming).
- Workflow runs tests/lint before build; failed checks do not publish.
- Deploy targets (Coolify, etc.) pull the published image — deployment itself is out of band unless wired later.

## Implementation order

1. Postgres, SQLAlchemy, Alembic, settings
2. Auth — users, sessions, `GET /me`, bearer dependency
3. BYOK — crypto service, settings endpoints
4. Game lobby — create, join, character PATCH, start (exposition)
5. Turn loop — actions, pass, auto DM round, adjudication
6. End conditions — death, mission complete
7. Export / import
8. Remove legacy `/init`, `/continue`, and env-based default API key
9. Dockerfile, CORS config, GHCR publish workflow on push to main

## Out of scope for v1

- WebSockets (clients poll `GET /games/{id}`)
- OAuth and external identity providers
- Server `OPENAI_API_KEY` except optional local dev fallback

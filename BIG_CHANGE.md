# Big Change

Replace the stateless single-player story API with a **client-agnostic FastAPI service backed by PostgreSQL**. The server is the source of truth for users, games, and turns. Clients authenticate with bearer tokens and call a clean REST API.

## Goals

### Multiplayer turns

- **Player round:** every alive player submits one action or passes.
- **Per-action adjudication:** each submitted `act` is adjudicated immediately; rejected actions return a reason and may be retried during the same player round.
- **DM round:** after all alive players have one accepted action (or pass), the server resolves the accepted set and advances the world.
- Rejected actions do not become player beats.

### Characters

- Characters are reusable entities owned by a user (`POST /characters` with freeform name + description).
- Creating or joining a game requires selecting an alive character that is not already in a game.
- Party size is capped at **5 players total** (including host).
- Character death is permanent: a dead character cannot join future games.
- Leaving a game abandons (clears `game_id`) without killing the character. Join is lobby-only, so abandoned characters cannot rejoin an in-progress game.
- On game end, all cast members have `game_id` cleared.

### End conditions

- Character death is decided contextually by the AI DM narrator from story outcomes and beats (no HP/stats in v1). Dead characters can no longer act and cannot join future games.
- Game ends if **all players die**.
- Game ends if the AI DM narrator determines the **story arc has reached its end** (mission accomplished), based on story progression and beats (not a numeric objective tracker in v1).
- Ended games are read-only.

### Bring your own API key (BYOK)

- Remove the server-wide `OPENAI_API_KEY` as the default way to play.
- Each user may store multiple provider keys (V1 provider set contains only OpenAI).
- Users can add keys and delete keys from their account settings.
- The server persists only the key record plus non-sensitive metadata needed for UX and operations.
- The server never returns plaintext key material to clients; list/read responses include only key metadata such as ID, vendor, and last four characters.
- On each LLM call the server loads the creator-selected key for that game, calls the API, and discards plaintext from memory immediately after use.
- Users do not re-enter their key for every new game.
- Creating a game requires the creator to have at least one key configured and to choose `api_key_id` for that game.
- Players who only join existing games do not need an API key.

## Architecture

```text
Client (any)  ──Bearer token──►  FastAPI  ──►  PostgreSQL
     │                              │
     │                              └── Narrator (LLM, per-request host key)
     │
     └── Local dev: `web` service (static reference UI on :3000)
```

- **Routers** are thin; **services** enforce game rules, membership, phases, and key presence.
- Reuse narrative types (`Exposition`, `RoundBeat`, `Story`) as DTOs; persist exposition as typed columns on `games` and beats in append-only tables.
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
GET    /me/settings/api-keys
POST   /me/settings/api-keys     # plaintext in, never out
DELETE /me/settings/api-keys/{key_id}
```

### Characters

```http
POST   /characters
GET    /characters
GET    /characters/{character_id}
PATCH  /characters/{character_id}
DELETE /characters/{character_id}
```

### Games

```http
POST   /games                      # seed + api_key_id + character_id
GET    /games
GET    /games/{game_id}
POST   /games/{game_id}/join       # body: { character_id }
POST   /games/{game_id}/leave      # abandon (does not kill)
POST   /games/{game_id}/start      # host only; runs exposition, opens play
POST   /games/{game_id}/actions    # act or pass during player round
```

`POST /games/{game_id}/join` is lobby-only. If the game is already started (`active` or `ended`), return `409 Conflict` with a descriptive error indicating that joining is closed after game start.

### Health

```http
GET /health
```

## Game lifecycle

```text
lobby → active → ended
         │
         └── player_round ⇄ dm_round
                         └→ resolution_failed ─→ dm_round (retry) (repeat until ended)
```

| Phase | Behaviour |
|-------|-----------|
| `lobby` | Join/leave with characters; host starts when ready; max 5 players total |
| `player_round` | Each alive character submits one action or pass |
| `dm_round` | Server resolves accepted actions and narrates outcomes |
| `resolution_failed` | DM resolution failed; game is paused until retry or recovery |
| `ended` | Read-only; reason is `all_dead` or `mission_complete`; cast `game_id`s cleared |

When the last alive player acts in a round, the server acknowledges quickly and transitions the game to `dm_round`.
Clients then poll `GET /games/{id}` for progress until the game returns to `player_round`, reaches `ended`, or enters `resolution_failed`.

## Canonical contract (single source of truth)

This section is the canonical API contract for phase transitions, poll response shape, and endpoint capabilities. Companion docs must reference this section and must not redefine or alias these rules.

### Canonical routing

- Exactly one join endpoint exists in v1: `POST /games/{game_id}/join`.
- There is no `POST /games/join` alias in v1.
- Join links are client UX only; clients must resolve any shared token/code to `game_id` before calling `POST /games/{game_id}/join`.

### Immutable phase transitions (machine-readable)

```yaml
phase_transitions:
  lobby:
    allowed_next: [player_round, ended]
    triggers:
      host_starts_game: player_round
      lobby_closed_or_deleted: ended
  player_round:
    allowed_next: [dm_round, ended]
    triggers:
      all_alive_players_have_accepted_action: dm_round
      all_players_dead_before_dm: ended
  dm_round:
    allowed_next: [player_round, resolution_failed, ended]
    triggers:
      dm_resolution_success_and_story_continues: player_round
      dm_resolution_failure: resolution_failed
      mission_complete_or_all_dead: ended
  resolution_failed:
    allowed_next: [dm_round, ended]
    triggers:
      host_retry_resolution: dm_round
      unrecoverable_failure_or_admin_stop: ended
  ended:
    allowed_next: []
    triggers: {}
```

### `GET /games/{game_id}` round status shape (machine-readable)

```json
{
  "id": "game-uuid",
  "status": "lobby|active|ended",
  "phase": "lobby|player_round|dm_round|resolution_failed|ended",
  "round_number": 3,
  "round_state": {
    "status": "actions_pending|resolving_round|resolved|resolution_failed",
    "error_code": "number|null",
    "error_code_name": "string|null",
    "error_message": "string|null",
    "retryable": "boolean|null",
    "attempt_count": "number|null"
  },
  "players": [
    {
      "user_id": "user-uuid",
      "is_alive": true,
      "life_state": "alive|dead",
      "death_round": "number|null",
      "death_summary": "string|null",
      "action_submitted": false
    }
  ]
}
```

Invariants:

- `phase=player_round` => `round_state.status=actions_pending`
- `phase=dm_round` => `round_state.status=resolving_round`
- `phase=resolution_failed` => `round_state.status=resolution_failed`
- `phase=ended` => game is read-only; all mutation endpoints return `409 Conflict`
- During `dm_round`, players already marked dead remain in `players[]` with `is_alive=false`, `life_state=dead`, and their death metadata populated.

### Round resolution error codes (numeric enum)

```yaml
round_resolution_error_codes:
  1001:
    name: llm_provider_unavailable
    description: LLM provider is temporarily unavailable or unreachable.
  1002:
    name: insufficient_credits
    description: Provider account has insufficient credits or quota.
  1003:
    name: rate_limited
    description: Provider rate limit was exceeded.
  1004:
    name: timeout
    description: LLM request timed out before completion.
  1005:
    name: internal_error
    description: Internal server error during DM resolution.
  1006:
    name: api_key_not_found
    description: Game references an API key record that no longer exists.
  1007:
    name: api_key_not_valid
    description: Stored API key is rejected by the provider as invalid.
```

### Endpoint capabilities (machine-readable)

```yaml
endpoint_capabilities:
  "GET /me":
    auth: required
    roles: [any_authenticated_user]
  "GET /me/settings":
    auth: required
    roles: [any_authenticated_user]
  "GET /me/settings/api-keys":
    auth: required
    roles: [any_authenticated_user]
  "POST /me/settings/api-keys":
    auth: required
    roles: [any_authenticated_user]
  "DELETE /me/settings/api-keys/{key_id}":
    auth: required
    roles: [key_owner]
  "POST /games":
    auth: required
    roles: [any_authenticated_user, api_key_owner]
    phases_allowed: [none]
  "GET /games":
    auth: required
    roles: [any_authenticated_user]
  "GET /games/{game_id}":
    auth: required
    roles: [game_member]
  "POST /games/{game_id}/join":
    auth: required
    roles: [any_authenticated_user_not_member]
    phases_allowed: [lobby]
  "POST /games/{game_id}/leave":
    auth: required
    roles: [game_member]
    phases_allowed: [lobby, player_round, dm_round, resolution_failed]
  "POST /characters":
    auth: required
    roles: [any_authenticated_user]
  "POST /games/{game_id}/start":
    auth: required
    roles: [game_host]
    phases_allowed: [lobby]
  "POST /games/{game_id}/actions":
    auth: required
    roles: [alive_active_player]
    phases_allowed: [player_round]
  "POST /games/{game_id}/retry-resolution":
    auth: required
    roles: [game_host]
    phases_allowed: [resolution_failed]
```

### OpenAPI and SDK

- FastAPI exposes OpenAPI automatically (`/openapi.json` and Swagger UI).
- SDK generation/publishing is postponed to a later version unless explicitly required in v1.

## Database (minimal)

```text
users
  id, email, password_hash, display_name
  created_at, updated_at

api_keys
  id, user_id
  vendor                   — openai (enum in V1)
  api_key                  — stored secret (never returned by API)
  last_four                — last 4 chars of plaintext key
  created_at, updated_at

sessions
  id, user_id, token_hash, expires_at, created_at

games
  id, host_user_id, seed
  api_key_id    — selected at game creation; used for all LLM calls in that game
  created_at
  — write-once exposition columns (nullable until start):
    time, place, world_rules, status_quo, backstory, conflict_seed,
    stakes, tone, genre, inciting_context
    other_characters, relationships, theme_hints, rules_of_conflict, foreshadowing  — TEXT[]

game_runtime                 # mutable control plane (1:1 with games)
  game_id PK/FK
  status       — lobby | active | ended
  phase        — lobby | player_round | dm_round | resolution_failed | ended
  end_reason   — null | all_dead | mission_complete
  updated_at

characters                   # reusable; owned by user
  id, user_id
  name (1–32), description (1–4000)
  game_id      — nullable current game
  is_alive, death_summary
  joined_at    — when joined current game; null when free
  created_at, updated_at

story_beats                  # append-only
  id, game_id, round_number, narrator_text, created_at
  UNIQUE (game_id, round_number)

story_beat_actions
  id, story_beat_id, character_id
  character_name             — snapshot
  action_type                — act | pass
  action_text

pending_actions              # current player round only
  id, game_id, character_id
  action_type              — act | pass
  action_text              — required when action_type=act; NULL when action_type=pass
  created_at

round_resolution_failures
  id, game_id, round_number
  error_code               — numeric enum (see round_resolution_error_codes)
  error_code_name          — llm_provider_unavailable | insufficient_credits | rate_limited | timeout | internal_error | api_key_not_found | api_key_not_valid
  error_message            — user-safe message
  retryable                — boolean
  attempt_count            — int
  failed_at
```

Current round number is derived as `max(story_beats.round_number) + 1` (0 before any beat / in lobby).

## Narrator changes

Extend the existing `Narrator` abstraction:

- `adjudicate_action(story, exposition, character, action_text)` — adjudicate each submitted `act` immediately with accept/reject + reason
- `generate_dm_beat(story, results)` — return narrator text for the round (actions persisted by caller)
- `evaluate_progress(story, alive_character_ids)` — deaths and mission completion from beats

## Local development (Docker Compose)

The repository ships a **Docker Compose** stack so the full system runs locally with one command — no host Postgres or Python install required.

```text
Browser  →  web (static)  ──►  api (FastAPI)  ──►  postgres
                                    ▲
                                    └── migrate (Alembic, one-shot)
```

### Services

| Service | Image / build | Role |
|---------|---------------|------|
| `postgres` | `postgres:16-alpine` | Primary database; data in a named Docker volume |
| `migrate` | same as `api` | One-shot: waits for Postgres health, runs `alembic upgrade head`, exits |
| `api` | `Dockerfile` | FastAPI app; starts only after `migrate` succeeds |
| `web` | `frontend/Dockerfile` (nginx) | Simple static UI for manual testing and API exploration |

`migrate` is a separate compose service (not baked into the API entrypoint) so failed migrations are visible in logs and do not leave a half-started API process.

### Quick start

```bash
cp .env.example .env   # set DATABASE_URL, SESSION_SECRET, CORS_ORIGINS
docker compose up --build
```

| URL | Purpose |
|-----|---------|
| `http://localhost:3000` | Web UI (register, lobby, play, settings) |
| `http://localhost:8000` | API |
| `http://localhost:8000/docs` | Swagger UI |

`make start`, `make stop`, `make logs`, and `make migrate` wrap the same compose commands.

### Compose wiring

```yaml
# docker-compose.yml (conceptual)
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ghostloom
      POSTGRES_PASSWORD: ghostloom
      POSTGRES_DB: ghostloom
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ghostloom -d ghostloom"]
      interval: 2s
      timeout: 5s
      retries: 10

  migrate:
    build: .
    command: alembic upgrade head
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy

  api:
    build: .
    ports: ["8000:8000"]
    env_file: .env
    depends_on:
      migrate:
        condition: service_completed_successfully

  web:
    build: ./frontend
    ports: ["3000:80"]
    environment:
      API_URL: http://localhost:8000   # browser-visible base URL for fetch()
    depends_on:
      - api
```

### Environment (local)

```bash
# .env.example
DATABASE_URL=postgresql+psycopg://ghostloom:ghostloom@postgres:5432/ghostloom
SESSION_SECRET=dev-only-change-me
CORS_ORIGINS=http://localhost:3000
# Optional local fallback while BYOK is being built; not used in production
OPENAI_API_KEY=
```

- `DATABASE_URL` uses the compose service hostname `postgres` (not `localhost`) from inside containers.
- `CORS_ORIGINS` must include the web UI origin so browser `fetch` with bearer tokens works.
- Secrets stay in `.env` (gitignored); `.env.example` documents required keys only.

### API container

- **Production image** (`Dockerfile`): installs deps, runs `uvicorn app.main:app`.
- **Migrations**: owned by the `migrate` service; the API image includes Alembic but does not auto-migrate on boot.
- **Dev override** (optional `docker-compose.override.yml`, gitignored): bind-mount `./app`, run uvicorn with `--reload`.

### Simple frontend (`frontend/`)

A minimal reference client — not the production game product, but enough to exercise the v1 API end-to-end.

**Tech:** static HTML/CSS/JS (or a thin Vite shell) served by nginx; no framework requirement beyond `fetch` and local state.

**Screens / flows:**

| Area | Behaviour |
|------|-----------|
| Auth | Register, login, logout; store bearer token in `sessionStorage` |
| Settings | List API keys (metadata only), add key, delete key |
| Characters | Create/list/delete freeform characters |
| Games | List games, create (seed + `api_key_id` + `character_id`), join with character, open game detail |
| Lobby | Wait for host to start; show party descriptions |
| Play | Poll `GET /games/{id}` during `dm_round`; submit act/pass in `player_round`; show resolution errors and host retry |
| Ended | Read-only story view |

The web container injects `API_URL` (or equivalent) at runtime so the same build works against local compose and staged APIs.

### Volumes and reset

- `pgdata` volume persists between `docker compose down`; use `make clean` / `docker compose down -v` to wipe local DB.
- After a wipe, `migrate` recreates schema on the next `up`.

## Deployment

Both the API and the reference web UI ship as **Docker images** and deploy to a container host (e.g. Coolify) as separate applications.

### API

- One image runs the FastAPI app; PostgreSQL is a separate service (managed DB or container).
- Migrations run as a one-shot job before or during deploy (Coolify pre-deploy command, or a dedicated `migrate` service) — not on every API request.
- Configuration via environment variables (database URL, session secret, CORS origins).

### Web (reference UI)

- The `frontend/Dockerfile` produces a small **nginx** image serving static HTML/CSS/JS.
- Deploy as a **second Coolify resource** on its own domain (e.g. `app.ghostloom.com` or `ghostloom.com`), separate from the API.
- Coolify treats it like any other Dockerfile app: build (or pull from GHCR), expose port 80, attach the public hostname.
- Set `API_URL` to the **browser-visible** API origin (e.g. `https://api.ghostloom.com`) — not an internal Docker hostname.
- No database, migrations, or secrets beyond the public API base URL.

### Cross-origin

- **Cross-origin clients** must be allowed: the API may live on a subdomain (e.g. `api.ghostloom.com`) while the web UI and other clients run on other domains or subdomains (e.g. `ghostloom.com`, `ghostloomgame.com`).
- CORS is configured explicitly on the API — allowed origins come from env (not `*` in production) and include credentials/headers needed for bearer auth. The web UI's public origin must be listed in `CORS_ORIGINS`.

## CI/CD

On every push to **`main`**, GitHub Actions builds Docker images and publishes them to **GitHub Container Registry (GHCR)**.

| Image | Package (example) | Deployed to |
|-------|-------------------|-------------|
| API | `ghcr.io/<org>/ghostloom-api` | Coolify — API app + migrate job |
| Web | `ghcr.io/<org>/ghostloom-web` | Coolify — static UI app |

- Image tags: commit SHA; also tag `latest` on main.
- Workflow runs tests/lint before build; failed checks do not publish.
- Coolify (or similar) pulls the published images — deployment wiring is out of band unless automated later.
- The web image build passes `API_URL` at **runtime** via Coolify env vars, not at image build time, so one image works across staging and production.

## Implementation order

1. Postgres, SQLAlchemy, Alembic, settings
2. Docker Compose local stack — `postgres`, `migrate`, `api`; `.env.example` with `DATABASE_URL` and `SESSION_SECRET`
3. Auth — users, sessions, `GET /me`, bearer dependency
4. BYOK — crypto service, settings endpoints
5. Game lobby — create/join with character_id, start (exposition)
6. Turn loop — actions, pass, auto DM round, adjudication
7. End conditions — death, mission complete
8. Simple frontend — `frontend/` nginx image, auth + lobby + play flows against the API
9. Remove legacy `/init`, `/continue`, and env-based default API key
10. Dockerfile polish, CORS config, GHCR publish workflow on push to main

## Out of scope for v1

- WebSockets (clients poll `GET /games/{id}`)
- OAuth and external identity providers
- Server `OPENAI_API_KEY` except optional local dev fallback

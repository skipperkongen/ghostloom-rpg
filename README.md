# Ghostloom

Multiplayer narrative game service backed by PostgreSQL. Players authenticate with bearer tokens, bring their own OpenAI API key, join game lobbies, and take turns in a shared story.

## Quick start (Docker Compose)

```bash
cp .env.example .env
# Generate a Fernet key for BYOK_ENCRYPTION_KEY:
# uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
docker compose up --build
```

| URL | Purpose |
|-----|---------|
| http://localhost:3000 | Reference web UI |
| http://localhost:8000 | API |
| http://localhost:8000/docs | Swagger UI |

### Make targets

```bash
make start      # docker compose up -d --build
make stop       # docker compose down
make logs       # API logs
make logs-all   # all service logs
make migrate    # run alembic upgrade head
make clean      # down -v (wipe DB volume)
```

## Architecture

```text
Browser → web (Vite/nginx :3000) → api (FastAPI :8000) → postgres
                                           ↑
                                    migrate (Alembic)
```

- **Auth**: email/password sessions with bearer tokens
- **BYOK**: users store encrypted OpenAI keys; game creator selects a key per game
- **Gameplay**: lobby → player rounds (act/pass with adjudication) → DM resolution → repeat until ended

See [BIG_CHANGE.md](BIG_CHANGE.md) for the full API contract.

## API overview

### Auth
- `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`
- `GET /me`

### Settings
- `GET/POST /me/settings/api-keys`, `DELETE /me/settings/api-keys/{id}`

### Characters
- `POST /characters`, `GET /characters`, `GET/PATCH/DELETE /characters/{id}`

### Games
- `POST /games`, `GET /games`, `GET /games/{id}`
- `POST /games/{id}/join`, `POST /games/{id}/leave`
- `POST /games/{id}/start`
- `POST /games/{id}/actions`, `POST /games/{id}/retry-resolution`

## Local development (without Docker)

```bash
uv sync --group dev
export DATABASE_URL=postgresql+psycopg://ghostloom:ghostloom@localhost:5432/ghostloom
export SESSION_SECRET=dev-only-change-me
export BYOK_ENCRYPTION_KEY=$(uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
alembic upgrade head
uvicorn app.main:app --reload
```

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `SESSION_SECRET` | Yes | Secret for session token hashing |
| `BYOK_ENCRYPTION_KEY` | Yes | Fernet key for encrypting stored API keys |
| `CORS_ORIGINS` | Yes | Comma-separated allowed origins |
| `OPENAI_API_KEY` | No | Optional dev fallback when BYOK key unavailable |

## Tests

```bash
# Requires Postgres (e.g. docker compose up postgres -d)
export TEST_DATABASE_URL=postgresql+psycopg://ghostloom:ghostloom@localhost:5432/ghostloom_test
uv run pytest
```

## Deployment

Docker images are published to GHCR on push to `main`:
- `ghcr.io/skipperkongen/ghostloom-api`
- `ghcr.io/skipperkongen/ghostloom-web`

Run migrations as a one-shot job before starting the API. Set `API_URL` on the web container to the browser-visible API origin.

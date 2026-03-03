# Story Engine Service

> Future work: reimplement in typescript and run entirely in browser with bring-your-own API key and local storage. Need safe way to store user's API key.

A small FastAPI service that generates and continues interactive stories using an LLM-backed narrator.

The service is intentionally simple: the client sends a `seed` to start a story, then sends the evolving `story` plus `user_input` to continue it. State is passed back and forth in the request/response body rather than stored in a database.

## Quickstart: try the demo

1. **Start the API** (pick one):
   - Python: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
   - Docker: `docker compose up --build`
   - Makefile: `make start`

2. **Option A – Bruno/Postman client**
   - Open the `bruno/Ghostloom` collection in Bruno and run:
     - `Health` → check `GET /health`
     - `Init` → call `POST /init` with a `seed`
     - `Continue` → call `POST /continue` with the returned `story` and your next input
   - If you prefer Postman, recreate the same three requests there using the endpoint and bodies shown below.

3. **Option B – Browser client**
   - With the API running on `http://localhost:8000`, open `index.html` in your browser (e.g. double‑click the file or serve it with a simple static server).
   - Use the UI to start a story and send follow‑up inputs; it talks directly to `POST /init` and `POST /continue`.

## Concept

- **LLM-driven**: Narrative text and progression are produced by a narrator abstraction.
- **Simple state model**: The entire story so far is sent on each `continue` call.
- **HTTP API first**: Designed to be easy to call from a browser, game client, or scripting environment.

## Project Structure

```text
ghostloom/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI app, routes, wiring
│   ├── narrator.py      # Narrator interface + DummyNarrator
│   └── models/          # Pydantic request/response models
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── requirements.txt
├── index.html           # Simple browser client
├── .env.example         # Example environment configuration
└── README.md
```

## API Endpoints

### `GET /health`

Health check endpoint.

**Response:**
```json
{
  "status": "healthy"
}
```

### `POST /init`

Start a new story from a seed prompt.

**Request body:**
```json
{
  "seed": "A mysterious adventure in a cyberpunk city"
}
```

**Response body** (see `StoryResponse` in `app/models`):
```json
{
  "story": "You find yourself in a neon‑lit alley in the heart of a sprawling cyberpunk city..."
}
```

### `POST /continue`

Continue an existing story with new user input.

**Request body:**
```json
{
  "story": "Previous story text here...",
  "user_input": "explore the control room"
}
```

**Response body:**
```json
{
  "story": "Extended story text here..."
}
```

## Local Development

### Prerequisites

- Python 3.11+
- Optional: Docker and Docker Compose (for container-based workflow)

### Setup

1. **Clone the repository** (if not already done):
   ```bash
   git clone <repository-url>
   cd ghostloom-rpg
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies** (either via `requirements.txt` or the package):
   ```bash
   pip install -r requirements.txt
   # or
   pip install .
   ```

4. **Configure environment variables**:

   Use the provided example file:

   ```bash
   cp .env.example .env
   ```

   The only relevant variable today is:

   - `OPENAI_API_KEY` (optional, for a real LLM-backed narrator implementation)

5. **Run the server**:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

6. **View API documentation**:
   Open `http://localhost:8000/docs` in your browser for interactive API documentation.

### Running with Docker Compose

If you prefer to run everything in a container:

1. Ensure Docker and Docker Compose are installed.
2. From the project root, run:

   ```bash
   docker compose up --build
   ```

3. The API will be available at `http://localhost:8000`, and docs at `http://localhost:8000/docs`.

To stop the service:

```bash
docker compose down
```

### Using the Makefile helpers

The `Makefile` provides convenience targets that wrap `docker compose`:

- **List targets**:

  ```bash
  make help
  ```

- **Start the service (detached)**:

  ```bash
  make start
  ```

- **View logs**:

  ```bash
  make logs
  ```

- **Stop the service**:

  ```bash
  make stop
  ```

- **Clean and rebuild everything**:

  ```bash
  make rebuild
  ```

## Environment Variables

| Variable        | Required | Description                                               |
|----------------|----------|-----------------------------------------------------------|
| `OPENAI_API_KEY` | No       | API key for a real LLM-backed narrator (optional today). |

## Narrator / LLM Integration

The narrator abstraction and default `DummyNarrator` are implemented in `app/narrator.py`. To plug in a real LLM:

1. Implement a class that satisfies the `Narrator` interface.
2. Wire it up in `app.main` instead of `DummyNarrator`, using `Settings.llm_api_key` for configuration.

This keeps the HTTP surface area stable while allowing experimentation with different model providers.


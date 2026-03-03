# Story Engine Service

> Future work: reimplement in typescript and run entirely in browser with bring-your-own API key and local storage. Need safe way to store user's API key.

A small FastAPI service that generates and continues interactive stories using an LLM-backed narrator.

The service is intentionally simple: the client sends a `seed` to start a story, then sends the evolving `story` plus `user_input` to continue it. State is passed back and forth in the request/response body rather than stored in a database.

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
- Optional: Docker and Docker Compose

### Setup

1. **Clone the repository** (if not already done):
   ```bash
   git clone <repository-url>
   cd ghostloom
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

   - `LLM_API_KEY` (optional, for a real LLM-backed narrator implementation)

5. **Run the server**:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

6. **View API documentation**:
   Open `http://localhost:8000/docs` in your browser for interactive API documentation.

## Deployment to DigitalOcean App Platform

### Prerequisites

- DigitalOcean account
- `doctl` CLI tool installed (optional, for CLI deployment)

### Deployment Steps

1. **Prepare your code**:
   - Ensure all code is committed to your git repository
   - The repository should contain:
     - `Dockerfile`
     - `app/` directory with all application code
     - `requirements.txt`

2. **Create a DigitalOcean App**:

   **Option A: Using the Web UI**
   
   - Go to [DigitalOcean App Platform](https://cloud.digitalocean.com/apps)
   - Click "Create App"
   - Connect your GitHub/GitLab repository
   - Select the repository and branch
   - DigitalOcean should auto-detect the Dockerfile
   - Configure the app:
     - **Name**: `story-engine` (or your preferred name)
     - **Type**: Web Service
     - **Dockerfile Path**: `Dockerfile`
     - **HTTP Port**: `8000`
   
   **Option B: Using `app.yaml`** (recommended for reproducibility)
   
   Create an `app.yaml` file in the root:
   ```yaml
   name: story-engine
   services:
     - name: api
       source_dir: /
       github:
         repo: your-username/ghostloom
         branch: main
       run_command: uvicorn app.main:app --host 0.0.0.0 --port 8000
       environment_slug: python
       instance_count: 1
       instance_size_slug: basic-xxs
       http_port: 8000
       routes:
         - path: /
       envs:
         - key: STATE_SECRET_KEY
           scope: RUN_TIME
           type: SECRET
         - key: LLM_API_KEY
           scope: RUN_TIME
           type: SECRET
   ```

3. **Set Environment Variables**:
   - In the App Platform UI, go to your app's Settings → App-Level Environment Variables
   - Add the following:
     - `LLM_API_KEY`: Optional, for when you replace the dummy narrator with a real LLM client.

4. **Deploy**:
   - If using the web UI: Click "Create Resources" or "Deploy"
   - If using `doctl`:
     ```bash
     doctl apps create --spec app.yaml
     ```

5. **Verify Deployment**:
   - Once deployed, DigitalOcean will provide a URL like `https://story-engine-xyz.ondigitalocean.app`
   - Test the health endpoint:
     ```bash
     curl https://your-app-url.ondigitalocean.app/health
     ```

### Important Notes for Production

- **HTTPS**: DigitalOcean App Platform provides HTTPS by default
- **Scaling**: Adjust `instance_count` and `instance_size_slug` in `app.yaml` based on your needs
- **Logs**: Monitor logs in the DigitalOcean App Platform dashboard

## Environment Variables

| Variable      | Required | Description                                               |
|--------------|----------|-----------------------------------------------------------|
| `LLM_API_KEY` | No       | API key for a real LLM-backed narrator (optional today). |

## Narrator / LLM Integration

The narrator abstraction and default `DummyNarrator` are implemented in `app/narrator.py`. To plug in a real LLM:

1. Implement a class that satisfies the `Narrator` interface.
2. Wire it up in `app.main` instead of `DummyNarrator`, using `Settings.llm_api_key` for configuration.

This keeps the HTTP surface area stable while allowing experimentation with different model providers.


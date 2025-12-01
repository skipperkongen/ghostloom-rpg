# Story Engine Service

A stateless narrative loop service that generates interactive stories using an LLM. The entire world state is stored in an opaque encrypted token passed between client and server, following the Markov property (no server-side session storage).

## Concept

This service implements a story engine where:

- **Stateless**: The server never stores session data in a database
- **Markov Property**: The entire world state is stored in a single opaque "state token" passed back and forth between client and server
- **Encrypted State**: Internal state is encrypted and authenticated using AES-GCM before being sent to the client
- **LLM-Driven**: Uses an LLM to generate narrative text and manage story progression

## Architecture

The service uses a simple abstraction for LLM clients, allowing easy swapping between stub implementations (for testing) and real LLM APIs (OpenAI, Anthropic, etc.). The internal state format is JSON understood only by the LLM - the server treats it as an opaque object to encrypt/decrypt.

## API Endpoints

### `GET /health`

Health check endpoint.

**Response:**
```json
{
  "status": "healthy"
}
```

### `POST /session/init`

Initialize a new story session.

**Request Body:**
```json
{
  "seed": "A mysterious adventure in a cyberpunk city"
}
```

**Response:**
```json
{
  "session_id": "abc123...",
  "round": 0,
  "state": "base64-encrypted-state-token...",
  "text": "You find yourself in space station. The atmosphere is tense. Nearby, you notice crew member looking in your direction. The air seems to hold secrets, and every shadow tells a story. Your journey begins here, shaped by the seed of your imagination: 'A mysterious adventure in a cyberpunk city'.\n\nWhat do you do next?"
}
```

### `POST /session/step`

Take a step in the story by providing an action.

**Request Body:**
```json
{
  "session_id": "abc123...",
  "round": 0,
  "state": "base64-encrypted-state-token...",
  "action": "explore the control room"
}
```

**Response:**
```json
{
  "session_id": "abc123...",
  "round": 1,
  "state": "new-base64-encrypted-state-token...",
  "text": "You explore the control room. The tense atmosphere of space station responds to your choice. Your actions ripple through the narrative, creating the first chapter of your tale. The story begins to take shape around you. Crew member observes your actions with interest.\n\nWhat path will you choose?"
}
```

## Project Structure

```
ghostloom/
├── app/
│   ├── __init__.py          # Package initialization
│   ├── main.py              # FastAPI app and routes
│   ├── models.py            # Pydantic request/response models
│   ├── crypto.py            # State token encryption/decryption
│   └── llm_client.py        # LLM abstraction + stub implementation
├── Dockerfile               # Docker container definition
├── docker-compose.yml       # Local development setup
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## Local Development

### Prerequisites

- Docker and Docker Compose installed
- Python 3.11+ (for local development without Docker)

### Setup

1. **Clone the repository** (if not already done):
   ```bash
   git clone <repository-url>
   cd ghostloom
   ```

2. **Create a `.env` file** in the root directory:
   ```bash
   # Generate a secret key for state encryption
   python -c "import secrets; print('STATE_SECRET_KEY=' + secrets.token_urlsafe(32))" > .env
   
   # Add LLM API key placeholder (optional for v1 with stub)
   echo "LLM_API_KEY=" >> .env
   ```

   Or manually create `.env`:
   ```
   STATE_SECRET_KEY=your-base64-encoded-32-byte-key-here
   LLM_API_KEY=
   ```

   To generate a secure key:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

3. **Run with Docker Compose**:
   ```bash
   docker compose up --build
   ```

   The service will be available at `http://localhost:8000`

4. **Test the API**:
   ```bash
   # Health check
   curl http://localhost:8000/health
   
   # Initialize a session
   curl -X POST http://localhost:8000/session/init \
     -H "Content-Type: application/json" \
     -d '{"seed": "A magical forest adventure"}'
   
   # Take a step (use session_id, round, and state from previous response)
   curl -X POST http://localhost:8000/session/step \
     -H "Content-Type: application/json" \
     -d '{
       "session_id": "your-session-id",
       "round": 0,
       "state": "your-state-token",
       "action": "look around"
     }'
   ```

5. **View API Documentation**:
   Open `http://localhost:8000/docs` in your browser for interactive API documentation.

### Development Without Docker

1. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set environment variables**:
   ```bash
   export STATE_SECRET_KEY="your-secret-key-here"
   export LLM_API_KEY=""
   ```

4. **Run the server**:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

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
     - `STATE_SECRET_KEY`: Your generated secret key (base64-encoded 32-byte key)
     - `LLM_API_KEY`: (Optional for v1, leave empty or set for future LLM integration)
   
   To generate a secure key:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

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

- **Secret Key Security**: Never commit `.env` files or expose `STATE_SECRET_KEY` in your code
- **HTTPS**: DigitalOcean App Platform provides HTTPS by default
- **Scaling**: Adjust `instance_count` and `instance_size_slug` in `app.yaml` based on your needs
- **Logs**: Monitor logs in the DigitalOcean App Platform dashboard

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `STATE_SECRET_KEY` | Yes | 32-byte secret key for encrypting/decrypting state tokens. Generate with: `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
| `LLM_API_KEY` | No (v1) | Placeholder for future LLM API integration. Not used by stub implementation. |

## State Token Format

The state token is:
1. Internal state (JSON) → Serialized to JSON string
2. Encrypted using AES-256-GCM with a 96-bit nonce
3. Base64 URL-safe encoded

The state includes at minimum:
- `seed`: The original user prompt
- `session_id`: Session identifier
- `round`: Current round number
- Additional fields managed by the LLM (opaque to the server)

## LLM Integration

The service uses an abstract `LLMClient` interface in `app/llm_client.py`. Currently, a `StubLLMClient` provides realistic story-like responses for testing. To integrate a real LLM:

1. Implement the `LLMClient` interface
2. Update `app/main.py` to instantiate your LLM client instead of `StubLLMClient`
3. Set the `LLM_API_KEY` environment variable

Example structure for future OpenAI integration:
```python
class OpenAILLMClient(LLMClient):
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)
    
    def init_story(self, seed: str) -> tuple[Dict[str, Any], str]:
        # Call OpenAI API...
        pass
```

## Error Handling

The API returns appropriate HTTP status codes:

- `200`: Success
- `400`: Bad request (invalid state token, round mismatch, etc.)
- `500`: Internal server error (LLM errors, encryption failures, etc.)

## License

[Add your license here]


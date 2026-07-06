# Big Change — Flows

Companion to [BIG_CHANGE.md](./BIG_CHANGE.md). That document defines architecture, API surface, and data model. **This document defines every user-visible flow in step-by-step detail** — preconditions, API calls, server behaviour, state changes, error cases, and client expectations.

Nothing here is implemented yet. When implementation diverges from this spec, update this file.

---

## Table of contents

1. [Actors and concepts](#actors-and-concepts)
2. [Game state machine](#game-state-machine)
3. [Authentication flows](#authentication-flows)
4. [Account and API key (BYOK)](#account-and-api-key-byok)
5. [Creating a game](#creating-a-game)
6. [Sharing a game](#sharing-a-game)
7. [Joining a game](#joining-a-game)
8. [Leaving a game](#leaving-a-game)
9. [Character creation and customisation](#character-creation-and-customisation)
10. [Importing a character from another game](#importing-a-character-from-another-game)
11. [Starting a game (exposition)](#starting-a-game-exposition)
12. [Polling game state](#polling-game-state)
13. [Submitting actions (player round)](#submitting-actions-player-round)
14. [AFK timeout and forced pass](#afk-timeout-and-forced-pass)
15. [DM round](#dm-round)
16. [Death and incapacitation](#death-and-incapacitation)
17. [End conditions](#end-conditions)
18. [Exporting a game](#exporting-a-game)
19. [Importing a game (full snapshot)](#importing-a-game-full-snapshot)
20. [Host permissions and edge cases](#host-permissions-and-edge-cases)
21. [Error catalogue](#error-catalogue)
22. [Decisions log](#decisions-log)

---

## Actors and concepts

| Actor | Description |
|-------|-------------|
| **User** | A registered account. Authenticates with a bearer token. |
| **Host** | The user who created the game (`games.host_user_id`). Pays for all LLM calls via their stored API key. Has exclusive rights to start the game and configure lobby settings. |
| **Player** | Any user with a row in `game_players` for a game. May or may not be the host. |
| **DM** | The LLM narrator. Not a user. Runs on the server using the host's unwrapped API key. Adjudicates actions, narrates rounds, tracks arc, detects deaths and mission completion. |
| **Client** | Any HTTP client (browser UI, Discord bot, Bruno). Polls `GET /games/{id}`; no WebSockets in v1. |

| Concept | Description |
|---------|-------------|
| **Character slot** | A playable role defined in exposition at game start. Each slot can be claimed by at most one player. |
| **Alive player** | `game_players.is_alive = true` and `game_players.status = active`. Only alive active players must act each round. |
| **AI-controlled player** | A player who left during active play. Their character is played by the DM on their behalf. |
| **Accepted action** | A player's act or pass that passed adjudication and is locked for the current round. |
| **Round** | One `player_round` followed by one `dm_round`. Numbered by `games.round_number` (starts at 1). |

### LLM cost rule

Every LLM call for a game uses the **host's** API key, even when triggered by a non-host player's action submission. The host must have a key configured before creating or starting a game.

---

## Game state machine

```text
                    POST /games/{id}/start
         ┌──────────────────────────────────────┐
         ▼                                      │
      lobby ──────────────────────────────► active
         │                                      │
         │                              ┌───────┴───────┐
         │                              ▼               │
         │                        player_round          │
         │                              │               │
         │                    all alive players          │
         │                    have accepted action       │
         │                              │               │
         │                              ▼               │
         │                          dm_round            │
         │                              │               │
         │              ┌───────────────┼───────────────┤
         │              ▼               ▼               │
         │         end condition    no end condition     │
         │         met              met                 │
         │              │               │               │
         │              ▼               └───────────────┘
         │            ended
         │
    join / leave /
    character setup
```

| `games.status` | `games.phase` | Meaning |
|----------------|---------------|---------|
| `lobby` | `lobby` | Waiting for players and character setup. Host can start. |
| `active` | `player_round` | Alive players submit actions or pass. |
| `active` | `dm_round` | Transient. Server is narrating; clients should not submit actions. |
| `ended` | `ended` | Game over. Read-only. |

`games.arc_phase` (`beginning` | `middle` | `end`) is narrative metadata updated by the DM each round. It is independent of `games.phase`.

---

## Authentication flows

### Register

**Trigger:** New user signs up.

**Request:**
```http
POST /auth/register
Content-Type: application/json

{
  "email": "player@example.com",
  "password": "…",
  "display_name": "Aria"
}
```

**Server behaviour:**
1. Validate email format and password minimum length (≥ 8 characters).
2. Reject if email already registered → `409 Conflict`.
3. Hash password (bcrypt or argon2).
4. Insert `users` row.
5. Create session; return bearer token.

**Response `201`:**
```json
{
  "access_token": "…",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "player@example.com",
    "display_name": "Aria"
  }
}
```

**Client behaviour:** Store `access_token`. Send `Authorization: Bearer …` on all subsequent requests.

---

### Login

**Request:**
```http
POST /auth/login
{ "email": "…", "password": "…" }
```

**Server behaviour:**
1. Look up user by email.
2. Verify password hash.
3. On failure → `401 Unauthorized` (generic message: "Invalid email or password").
4. Create new session row; return token.

**Response `200`:** Same shape as register.

---

### Logout

**Request:**
```http
POST /auth/logout
Authorization: Bearer …
```

**Server behaviour:** Delete or invalidate the session matching the token.

**Response `204`:** No body.

---

### Session validation (all protected routes)

On every authenticated request:
1. Extract bearer token from `Authorization` header.
2. Hash token; look up `sessions` where `token_hash` matches and `expires_at > now()`.
3. On failure → `401 Unauthorized`.
4. Resolve `user_id`; attach to request context.

Sessions expire after **30 days** of inactivity (configurable). Refresh is out of scope for v1 — client re-logs in.

---

## Account and API key (BYOK)

### View profile

**Request:** `GET /me`

**Response `200`:**
```json
{
  "id": "uuid",
  "email": "player@example.com",
  "display_name": "Aria",
  "api_key_configured": false,
  "api_key_hint": null
}
```

When a key is stored: `"api_key_configured": true`, `"api_key_hint": "…x7Qa"` (last four characters only).

---

### Add or replace API key

**Trigger:** User wants to host games (create or start).

**Request:**
```http
PUT /me/settings/api-key
Authorization: Bearer …

{ "api_key": "sk-…" }
```

**Server behaviour:**
1. Validate key format (non-empty, plausible OpenAI key prefix).
2. Optionally perform a lightweight OpenAI API test call (e.g. list models or minimal completion). On failure → `400 Bad Request` with `{ "detail": "API key rejected by provider: …" }`. Key is **not** stored.
3. Wrap key with AES-256-GCM using server `KEY_ENCRYPTION_SECRET`.
4. Store ciphertext in `users.wrapped_api_key`; store last-four hint in `users.api_key_hint`.
5. Plaintext key exists only in memory for the duration of this request; never logged.

**Response `200`:**
```json
{
  "api_key_configured": true,
  "api_key_hint": "…x7Qa"
}
```

**Client behaviour:** Show hint so user knows a key is saved. Never expect the full key back.

---

### Remove API key

**Request:** `DELETE /me/settings/api-key`

**Server behaviour:** Clear `wrapped_api_key` and `api_key_hint`.

**Response `204`.**

**Side effects:**
- User can no longer `POST /games` or `POST /games/{id}/start`.
- **In-progress games** where this user is host continue to work until the next LLM call fails (key gone). Practically: host should not delete key while games are active. Server returns `403` on `POST /games/{id}/start` if key missing; ongoing active games attempt LLM and return `502` if key unavailable.

---

### Flow summary: new host onboarding

```text
Register → Login → PUT /me/settings/api-key → GET /me (confirm hint) → POST /games
```

A user who only joins games others host **does not** need an API key.

---

## Creating a game

**Trigger:** Authenticated user with API key configured wants to host a new game.

**Preconditions:**
- `api_key_configured = true` on the requesting user.
- User is not required to be free of other games (a user may host or play multiple games).

**Request:**
```http
POST /games
Authorization: Bearer …

{
  "seed": "A haunted space station where the crew discovers an ancient signal",
  "max_players": 4,
  "turn_timeout_hours": 48
}
```

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `seed` | yes | — | Free-text prompt for exposition generation at start. 10–2000 characters. |
| `max_players` | no | `4` | Maximum players including host. Range 1–8. |
| `turn_timeout_hours` | no | `48` | Hours before AFK auto-pass (see [AFK flow](#afk-timeout-and-forced-pass)). Host can change in lobby. |

**Server behaviour:**
1. Verify API key configured → else `403 Forbidden`.
2. Generate `game_id` (UUID) and `join_code` (8-character alphanumeric, uppercase, unique).
3. Insert `games` row:
   - `host_user_id` = requester
   - `status` = `lobby`, `phase` = `lobby`
   - `seed`, `max_players`, `turn_timeout_hours`
   - `exposition` = null (generated at start)
   - `story_data` = `{ "beats": [] }`
   - `round_number` = 0
   - `arc_phase` = null
   - `end_reason` = null
4. Insert `game_players` row for host:
   - `character_slot_id` = null (no slots until start)
   - `character_name` = null
   - `character_description` = null
   - `is_alive` = true
   - `status` = `active`
   - `is_ai_controlled` = false

**Response `201`:**
```json
{
  "id": "game-uuid",
  "join_code": "H7K2M9XP",
  "status": "lobby",
  "phase": "lobby",
  "seed": "…",
  "max_players": 4,
  "turn_timeout_hours": 48,
  "host_user_id": "user-uuid",
  "player_count": 1,
  "created_at": "…"
}
```

**Client behaviour:** Display join code and offer share UI. Host proceeds to share link or wait for players.

---

## Sharing a game

There is no separate "share" API. Sharing is **client-side**: the host communicates the join code or a deep link.

**Join link format (client convention, not server route):**
```text
https://ghostloom.com/join/H7K2M9XP
```

The client extracts `H7K2M9XP` and calls `POST /games/join` (see below).

**What is shareable:**
- `join_code` — anyone with the code can join while the game is in lobby and not full.
- `game_id` — UUID; same join rules via `POST /games/{game_id}/join`.

**What is not shareable:**
- Bearer tokens
- API keys
- Export files containing secrets (export never includes these)

**Visibility:** `GET /games` returns only games the authenticated user is a member of. There is no public game browser in v1.

---

## Joining a game

### By join code (preferred)

**Request:**
```http
POST /games/join
Authorization: Bearer …

{ "join_code": "H7K2M9XP" }
```

### By game ID

**Request:**
```http
POST /games/{game_id}/join
Authorization: Bearer …
```

Both endpoints behave identically after resolving `game_id`.

**Preconditions:**
- Game `status` = `lobby`. → else `409 Conflict` ("Game has already started").
- `player_count < max_players`. → else `409 Conflict` ("Game is full").
- User not already a member. → else `409 Conflict` ("Already in this game").

**Server behaviour:**
1. Resolve game by `join_code` or `game_id`.
2. Insert `game_players` row:
   - `character_slot_id` = null
   - `character_name` = null
   - `character_description` = null
   - `is_alive` = true
   - `status` = `active`
   - `is_ai_controlled` = false
3. Return updated game summary.

**Response `200`:**
```json
{
  "id": "game-uuid",
  "status": "lobby",
  "phase": "lobby",
  "player_count": 2,
  "players": [
    {
      "user_id": "…",
      "display_name": "Host",
      "character_slot_id": null,
      "character_name": null,
      "is_host": true
    },
    {
      "user_id": "…",
      "display_name": "Aria",
      "character_slot_id": null,
      "character_name": null,
      "is_host": false
    }
  ]
}
```

**Client behaviour:** Navigate to lobby UI. Prompt player to claim a character slot after host starts (slots do not exist until start) — **or** let player draft name/description in lobby that will be validated against slots at start. See [Character creation](#character-creation-and-customisation).

**Late join:** Not supported in v1. Once `status` = `active`, join returns `409`.

---

## Leaving a game

**Request:**
```http
POST /games/{game_id}/leave
Authorization: Bearer …
```

**Preconditions:** User is a member of the game.

### Leaving during lobby

**Server behaviour:**
1. Delete `game_players` row for this user.
2. If leaver is host and other players remain → transfer `host_user_id` to the player who joined earliest (`joined_at` ASC).
3. If leaver is host and no players remain → delete game (cascade `game_players`, `pending_actions`).
4. Release any claimed slot (none exist pre-start).

**Response `200`:** `{ "left": true }` or full game state for remaining players if needed.

### Leaving during active play

**Server behaviour:**
1. Set `game_players.status` = `abandoned`.
2. Set `game_players.is_ai_controlled` = true.
3. Do **not** delete the row — character remains in the story.
4. If leaver is host → transfer `host_user_id` to earliest remaining `status = active` player. New host does **not** need their own API key; LLM continues using original host's wrapped key stored on the game (`games.api_key_user_id` — set at start to host at that time). See [Decisions log](#decisions-log).
5. Delete any `pending_actions` for this user in the current round (if they had a rejected action in progress, it is cleared).
6. If the current round is `player_round` and all remaining alive active/AI players now have accepted actions, trigger [DM round](#dm-round) immediately.

**AI takeover behaviour:**
- Each subsequent `player_round`, the server auto-generates an action for `is_ai_controlled` players before checking round completion.
- AI action is produced by LLM call: given character description, recent beats, and exposition, generate a plausible action consistent with the character. If LLM fails, fall back to `pass`.
- AI actions are adjudicated like player actions (immediate validation). On rejection, server retries once with a simpler pass-leaning prompt; if still rejected, force `pass`.

**Response `200`:**
```json
{
  "left": true,
  "game_id": "…",
  "ai_takeover": true
}
```

**Client behaviour (remaining players):** Show that the character is now AI-controlled. No action required from them.

---

## Character creation and customisation

Characters are tied to **slots** created at game start. In the lobby, players prepare; after start, they claim slots.

### Phase 1 — Lobby preparation (before start)

Players may set a draft character while waiting:

**Request:**
```http
PATCH /games/{game_id}/players/me
Authorization: Bearer …

{
  "character_name": "Dr. Elena Vasquez",
  "character_description": "Station xenobiologist, skeptical of authority, carries a battered datapad."
}
```

**Preconditions:**
- Game `status` = `lobby`.
- User is a game member.

**Server behaviour:**
1. Store `character_name` and `character_description` on `game_players`.
2. **No LLM validation yet** — exposition does not exist. Validation happens at start when slots are generated.

**Response `200`:** Updated player object.

Players may update draft freely until start.

---

### Phase 2 — Start generates slots (see [Starting a game](#starting-a-game-exposition))

When the host starts, the server generates exposition **and** `playable_characters` — a list of slots:

```json
{
  "playable_characters": [
    {
      "id": "slot-1",
      "name": "Dr. Elena Vasquez",
      "role": "Xenobiologist",
      "hook": "You noticed the signal hours before anyone else believed you."
    },
    {
      "id": "slot-2",
      "name": "Captain Okonkwo",
      "role": "Station commander",
      "hook": "The station's life-support budget is already stretched thin."
    }
  ]
}
```

Slot count = `player_count` at start time (one slot per current player). Names are starting suggestions; players customise.

`playable_characters` is stored inside `games.exposition` JSONB (extends the `Exposition` model).

---

### Phase 3 — Claim a slot (after start, still before round 1 actions)

Immediately after start, game is `active` / `player_round` but players must claim slots before submitting actions.

**Request:**
```http
PATCH /games/{game_id}/players/me
Authorization: Bearer …

{
  "character_slot_id": "slot-1",
  "character_name": "Dr. Elena Vasquez",
  "character_description": "Xenobiologist, skeptical, secretly recorded the signal."
}
```

**Preconditions:**
- Game `status` = `active`.
- Slot not claimed by another player.
- User has no slot yet, **or** is updating their own unvalidated customisation.

**Server behaviour:**
1. Assign `character_slot_id`.
2. Run **LLM character validation**: `validate_character(exposition, slot, name, description)`.
   - Checks: fits `world_rules`, `time`, `place`, `genre`, `tone`; no anachronistic tech/magic; no omnipotence; description consistent with slot `role` and `hook`.
3. On **accept** → `character_validated` = true. Player may submit actions.
4. On **reject** → `422 Unprocessable Entity`:
   ```json
   {
     "status": "rejected",
     "reason": "Cybernetic implants are inconsistent with this medieval fantasy setting.",
     "character_slot_id": "slot-1"
   }
   ```
   Player revises and retries `PATCH`.

**Slot claim deadline:** If a player has not claimed and validated a character by the time they try to submit an action → `409 Conflict` ("Claim and validate a character first").

**Unclaimed slots at start:** If `player_count` drops before start (someone left), slots match remaining players. No empty slots.

---

### Character validation rules (LLM prompt contract)

The `validate_character` call returns:

```json
{ "accepted": true }
```
or
```json
{
  "accepted": false,
  "reason": "Human-readable explanation for the player"
}
```

Validation is **setting-bound**, not plot-bound. A character may be ambitious or villainous; they may not break `world_rules`.

---

## Importing a character from another game

Distinct from [full game import](#importing-a-game-full-snapshot). This flow brings **one character's identity** from a prior game into a new game's lobby.

### Export character (source game)

**Request:**
```http
GET /games/{game_id}/players/me/export
Authorization: Bearer …
```

**Preconditions:**
- User is a member of the source game.
- User has a character with `character_name` set (lobby draft or validated).

**Response `200`:**
```json
{
  "format": "ghostloom-character",
  "version": 1,
  "exported_at": "…",
  "character": {
    "name": "Dr. Elena Vasquez",
    "description": "Xenobiologist, skeptical, carries a battered datapad.",
    "source_game_seed": "A haunted space station…",
    "source_genre": "Sci-fi horror",
    "source_tone": "Tense, claustrophobic"
  }
}
```

No plot state, inventory, beats, or secrets are exported. Only identity flavour.

---

### Import character (target game lobby)

**Request:**
```http
POST /games/{game_id}/players/me/import
Authorization: Bearer …

{
  "character_export": { … },
  "adapt_to_setting": true
}
```

**Preconditions:**
- Target game `status` = `lobby`.
- User is a member.

**Server behaviour:**
1. Parse and validate `format` = `ghostloom-character`, `version` = 1.
2. Store as draft `character_name` and `character_description` on `game_players`.
3. If `adapt_to_setting` = true and exposition exists (it does not in lobby — adaptation deferred) → **at game start**, when slots are generated, the server runs `adapt_character(exposition, imported_character)` to produce a slot-consistent description. Player reviews adapted description in the claim phase.
4. If `adapt_to_setting` = false → character is kept as-is; validated strictly at slot claim against new exposition.

**Response `200`:**
```json
{
  "character_name": "…",
  "character_description": "…",
  "adaptation_pending": true
}
```

**At start (host calls start):**
- For players with imported characters and `adapt_to_setting` = true, LLM rewrites description to fit the new seed while preserving personality and core identity.
- Player sees adapted text during slot claim; may edit before validation.

**Cross-genre example:** Space xenobiologist → "scholar of forbidden texts" in a fantasy seed. Player can reject adaptation and edit manually.

---

## Starting a game (exposition)

**Trigger:** Host decides the party is ready.

**Request:**
```http
POST /games/{game_id}/start
Authorization: Bearer …
```

**Preconditions:**
- Requester is `host_user_id`.
- Game `status` = `lobby`.
- Host has `api_key_configured` = true.
- `player_count` ≥ 1 (solo play allowed).
- Every current player has non-empty `character_name` and `character_description` (draft from lobby). → else `409` listing players not ready.

**Server behaviour:**
1. Set `games.api_key_user_id` = current `host_user_id` (key owner for all LLM calls in this game).
2. Call `Narrator.generate_exposition(seed)` → exposition JSON.
3. Generate `playable_characters` array with exactly `player_count` slots, informed by exposition and each player's draft name/description.
4. For imported characters with `adapt_to_setting`, run adaptation (see above).
5. Append opening narrator beat to `story_data.beats` (scene-setting, 1–2 sentences).
6. Update game:
   - `status` = `active`
   - `phase` = `player_round`
   - `round_number` = 1
   - `arc_phase` = `beginning`
   - `round_deadline_at` = now() + `turn_timeout_hours`
   - `exposition` = generated exposition including `playable_characters`
7. Do **not** auto-claim slots — players must `PATCH` to claim and validate.

**Response `200`:** Full game state (see [Polling](#polling-game-state)).

**Client behaviour:**
1. Show exposition to all players.
2. Guide each player to claim a slot and validate character.
3. Enable action input only after `character_validated` = true for the current user.

---

## Polling game state

Clients poll; no WebSockets in v1.

**Request:**
```http
GET /games/{game_id}
Authorization: Bearer …
```

**Preconditions:** User is a game member. → else `403`.

**Response `200` (active game, player round):**
```json
{
  "id": "…",
  "status": "active",
  "phase": "player_round",
  "round_number": 3,
  "arc_phase": "middle",
  "round_deadline_at": "…",
  "exposition": { "…": "…", "playable_characters": ["…"] },
  "story_data": {
    "beats": [
      { "role": "narrator", "text": "…" },
      { "role": "player", "text": "…", "character_name": "Elena" }
    ]
  },
  "players": [
    {
      "user_id": "…",
      "display_name": "Aria",
      "character_slot_id": "slot-1",
      "character_name": "Dr. Elena Vasquez",
      "is_alive": true,
      "status": "active",
      "is_ai_controlled": false,
      "character_validated": true,
      "action_submitted": true,
      "action_type": "act"
    },
    {
      "user_id": "…",
      "display_name": "Bob",
      "character_name": "Captain Okonkwo",
      "is_alive": true,
      "status": "active",
      "is_ai_controlled": false,
      "character_validated": true,
      "action_submitted": false
    }
  ],
  "my_pending_action": null,
  "host_user_id": "…"
}
```

| Field | Description |
|-------|-------------|
| `action_submitted` | True if player has an **accepted** action locked for this round. |
| `my_pending_action` | Current user's in-flight action this round. `null` if none. `{ "status": "rejected", "reason": "…", "action_text": "…" }` if last submit was rejected and they may retry. Never exposes other players' action text before DM round. |

**Poll interval:** Client chooses (e.g. every 3–5 seconds in player round, slower in lobby). Server does not push.

**During `dm_round`:** Response may show `"phase": "dm_round"` briefly. Client should disable input and poll until `player_round` or `ended`.

**Ended game:** Same endpoint; `status` = `ended`, `end_reason` = `all_dead` | `mission_complete`. All mutation endpoints return `409`.

---

## Submitting actions (player round)

### Overview

Each round, every **alive** player with `status` in (`active`, `abandoned` with `is_ai_controlled`) must lock exactly one **accepted** action before the DM round runs.

- **Act:** free-text action.
- **Pass:** explicit pass; always accepted without LLM adjudication.

**Critical rule — immediate adjudication:** When a player submits an **act**, the server validates it against the world setting **immediately**, before other players finish. The client receives accept or reject and can retry on reject. This supersedes the batch-adjudication wording in BIG_CHANGE.md.

Rejected actions are never stored as beats and do not count as having acted.

---

### Submit act

**Request:**
```http
POST /games/{game_id}/actions
Authorization: Bearer …

{
  "action_type": "act",
  "action_text": "I scan the signal with my datapad, trying to triangulate its source."
}
```

**Preconditions:**
- Game `status` = `active`, `phase` = `player_round`.
- User is alive (`is_alive` = true`).
- User `status` = `active` (not abandoned human — abandoned players are AI-controlled; server generates their actions).
- `character_validated` = true.
- User does not already have an accepted action this round. → else `409` ("Already acted this round").
- `action_text` length 1–500 characters.

**Server behaviour:**
1. Call `Narrator.adjudicate_action(story, exposition, character, action_text)`.
2. **If rejected:**
   - Upsert `pending_actions` with `adjudication` = `rejected`, `rejection_reason` set.
   - Return `422`:
     ```json
     {
       "status": "rejected",
       "reason": "Your datapad cannot detect signals through the jamming field established in round 2.",
       "can_retry": true
     }
     ```
   - Player may submit again (see retry).
3. **If accepted:**
   - Upsert `pending_actions` with `adjudication` = `accepted`, `action_text` stored.
   - Return `200`:
     ```json
     {
       "status": "accepted",
       "action_type": "act",
       "round_number": 3
     }
     ```
4. After accept, check if all alive players (including AI-controlled) have accepted actions. If yes → run [DM round](#dm-round) synchronously and return full game state in the same response (see below).

**Retry after rejection:**
- Player calls `POST /games/{game_id}/actions` again with revised text.
- Previous rejected `pending_actions` row is replaced.
- No limit on retries within the round deadline.

---

### Submit pass

**Request:**
```http
POST /games/{game_id}/actions
{ "action_type": "pass" }
```

**Preconditions:** Same as act, except no `action_text`.

**Server behaviour:**
1. Pass is always accepted. Store `pending_actions` with `action_type` = `pass`, `adjudication` = `accepted`.
2. Return `200` `{ "status": "accepted", "action_type": "pass" }`.
3. Check round completion; possibly trigger DM round.

---

### Response when DM round triggers on last acceptance

When the last player's action is accepted, the server runs the DM round before responding:

**Response `200`:**
```json
{
  "status": "accepted",
  "action_type": "act",
  "round_advanced": true,
  "game": { … full game state, round_number may increment, new narrator beat … }
}
```

---

### What other players see before DM round

`GET /games/{id}` shows `action_submitted: true | false` per player but **never** reveals `action_text` until after the DM round narrates outcomes. Pass is visible as `action_type: "pass"` only after round resolves if desired, or as submitted=true without type — **v1 choice:** show only `action_submitted` boolean during the round to reduce meta-gaming.

---

### Dead players

`is_alive` = false → `POST /actions` returns `403` ("Character is dead").

---

## AFK timeout and forced pass

**Purpose:** Prevent one absent player from blocking the game indefinitely.

### Configuration

- `turn_timeout_hours` set at game creation (default 48).
- Host may change in lobby: `PATCH /games/{game_id}` with `{ "turn_timeout_hours": 24 }` (host only, lobby only).

### Deadline

When a `player_round` begins, server sets:
```text
games.round_deadline_at = now() + turn_timeout_hours
```

Reset at the start of each new `player_round`.

### Enforcement

On **every** `GET /games/{id}`, `POST /actions`, and a periodic server-side check (every 15 minutes via background task):

1. If `phase` = `player_round` and `now() > round_deadline_at`:
2. For each alive player with `status` = `active` and `is_ai_controlled` = false who lacks an accepted action:
   - Create accepted `pending_actions` row: `action_type` = `pass`, note `forced_by_timeout` = true internally.
3. For AI-controlled players without actions, run AI action generation (or pass on failure).
4. If all players now have accepted actions → trigger [DM round](#dm-round).

**Client display:** In `GET /games/{id}`, include `"round_deadline_at"` so clients can show a countdown.

**Notification:** Out of scope for v1 (no email/push). Players discover on poll.

---

## DM round

**Trigger:** All alive players (active or AI-controlled) have an accepted action for the current round.

**Server behaviour (synchronous, single request):**

1. Set `games.phase` = `dm_round` (visible to pollers).
2. Collect all accepted `pending_actions` for this `round_number`.
3. Call `Narrator.generate_dm_beat(story, accepted_actions)`:
   - Input: full story, exposition, each character's action or pass.
   - Output: narrator beat text (1–3 sentences) describing what happens when actions resolve together.
   - Rejected actions are not in this list.
4. Append narrator beat to `story_data.beats`. Append player beats for each non-pass act (attributed by `character_name`).
5. Call `Narrator.evaluate_progress(story)`:
   - Update `arc_phase` if appropriate.
   - Set `is_alive` = false for any characters who died.
   - Determine `mission_complete` boolean.
6. **End check** (see [End conditions](#end-conditions)).
7. If game continues:
   - Increment `round_number`.
   - Clear all `pending_actions` for this game.
   - Set `phase` = `player_round`.
   - Set new `round_deadline_at`.
8. If game ended:
   - Set `status` = `ended`, `phase` = `ended`, `end_reason` accordingly.
   - Clear `pending_actions`.

**Client behaviour:** Poll until `phase` returns to `player_round` or `ended`. Display new beats.

**Duration:** LLM calls may take several seconds. Clients should show a "DM is narrating…" state when `phase` = `dm_round`.

---

## Death and incapacitation

- Death is determined by `evaluate_progress` during the DM round (LLM judges outcomes of dangerous actions).
- `game_players.is_alive` set to `false` permanently for this game (no respawn in v1).
- Dead characters:
  - Cannot submit actions.
  - Remain visible in player list and story.
  - `action_submitted` is irrelevant; they are skipped in round completion checks.
- **All dead** → end condition (see below).

---

## End conditions

After each DM round, the server evaluates:

### All players dead

**Condition:** Every `game_players` row has `is_alive` = false.

**Result:**
- `status` = `ended`
- `phase` = `ended`
- `end_reason` = `all_dead`

### Mission complete

**Condition:** `evaluate_progress` returns `mission_complete: true` (story objective from exposition `conflict_seed` / `stakes` fulfilled; arc reached satisfying conclusion).

**Result:**
- `status` = `ended`
- `phase` = `ended`
- `end_reason` = `mission_complete`

### Continuing

If neither condition met → next `player_round`.

### Ended game behaviour

| Endpoint | Behaviour |
|----------|-----------|
| `GET /games/{id}` | Allowed. Full history. |
| `GET /games/{id}/export` | Allowed. |
| `POST /actions` | `409` "Game has ended" |
| `PATCH /players/me` | `409` |
| `POST /join` | `409` |
| `POST /leave` | Allowed (cleanup membership; optional) |

**Client behaviour:** Show end screen with reason and full story. Read-only.

---

## Exporting a game

**Request:**
```http
GET /games/{game_id}/export
Authorization: Bearer …
```

**Preconditions:** User is a game member.

**Response `200`:**
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
    "players": [
      {
        "character_name": "…",
        "character_description": "…",
        "is_alive": true
      }
    ],
    "status": "active",
    "phase": "player_round",
    "end_reason": null
  }
}
```

**Never includes:** API keys, session tokens, `user_id`, email, wrapped keys.

**Use cases:** Backup, migration, sharing story snapshots. Import creates a **new** game.

---

## Importing a game (full snapshot)

**Request:**
```http
POST /games/import
Authorization: Bearer …

{ "export": { … } }
```

**Preconditions:**
- Requester has `api_key_configured` = true (becomes host).

**Server behaviour:**
1. Validate `format` = `ghostloom-game`, supported `version`.
2. Create new `games` row; requester is host and sole initial member.
3. Copy `seed`, `exposition`, `story_data`, `arc_phase`, `round_number`, `status`, `phase`, `end_reason` from snapshot.
4. Create `game_players` rows from snapshot player characters (no user mapping — importer must invite others again).
5. Generate new `join_code` and `game_id`.
6. Set `games.api_key_user_id` = importer.

**Response `201`:** New game summary.

**Note:** Imported active games do not restore other human players. Characters exist as data; humans must rejoin and reclaim slots in lobby if imported into lobby, or importer plays alone until others join. **v1 simplification:** Import always sets `status` = `lobby`, `phase` = `lobby`, `round_number` preserved in snapshot metadata but play restarts from imported story state in `story_data`. Players re-invited via join code.

---

## Host permissions and edge cases

| Action | Host only? |
|--------|------------|
| `POST /games/{id}/start` | yes |
| `PATCH /games/{id}` (timeout, max_players) | yes, lobby only |
| `POST /games/{id}/join` | any user |
| `POST /games/{id}/leave` | any member |
| `POST /games/{id}/actions` | any alive active player |
| `GET /games/{id}/export` | any member |

### Host transfer

When host leaves:
- `host_user_id` → earliest `joined_at` among remaining `status` = `active` players.
- `games.api_key_user_id` unchanged (original host's key still pays).
- If no active players remain → game ends or deletes (lobby: delete; active: `ended` / `all_dead` if everyone dead, else continue with AI players only).

### Solo play

`player_count` = 1 is valid. Rounds proceed with one human action + DM.

### Concurrent submits

Two players submitting simultaneously: database unique constraint on `(game_id, user_id, round_number)` for `pending_actions`. Each submission is independent. DM round triggers exactly once when the last acceptance completes — use transactional locking on game row.

### Idempotency

Submitting the same accepted action again → `409`. Submitting after round advanced → `409` "Round has advanced".

### Game in `dm_round`

`POST /actions` → `409` "DM round in progress".

---

## Error catalogue

| HTTP | Code / detail | When |
|------|---------------|------|
| `400` | Validation error | Malformed body, bad key format |
| `401` | Unauthorized | Missing/invalid token |
| `403` | Forbidden | Not a member; dead player acting; non-host starting; no API key |
| `404` | Not found | Unknown game or join code |
| `409` | Conflict | Wrong phase, already acted, game full, game started, game ended |
| `422` | Action rejected | LLM rejected character or action (body includes `reason`) |
| `502` | Bad gateway | LLM provider error |
| `503` | Service unavailable | Database unreachable |

---

## Decisions log

Explicit choices made in this document (for review):

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | **Immediate action adjudication** on submit, not batch at DM round | Better UX; player can retry before others finish. Updates BIG_CHANGE.md DM-round wording. |
| 2 | **Slot-based characters** generated at start | Ties players to exposition; avoids orphan characters. |
| 3 | **Lobby draft → validate at slot claim** | Exposition does not exist until start; cannot validate earlier. |
| 4 | **Join code** for sharing | Simple, no invite table. |
| 5 | **AI takeover on leave during active play** | Party continues; character stays in story. |
| 6 | **Host transfer on host leave** | Someone can start if host leaves in lobby; active games keep a nominal host. |
| 7 | **`api_key_user_id` pinned at start** | New host after transfer does not need their own key for ongoing game. |
| 8 | **AFK → forced pass** at `turn_timeout_hours` | Unblocks rounds; default 48h. |
| 9 | **Character import** is separate from game import | Different use case; exports identity only. |
| 10 | **No late join** after start | Reduces complexity in v1. |
| 11 | **Action text hidden from other players** until DM round | Reduces meta-gaming. |
| 12 | **Solo play allowed** | One player + DM is valid. |
| 13 | **Full game import resets to lobby** | Humans must rejoin; story state preserved. |

---

## Schema additions (beyond BIG_CHANGE.md)

This flows document requires these additions to the data model in BIG_CHANGE.md:

```text
games
  join_code              — unique, 8 chars
  max_players            — int, default 4
  turn_timeout_hours     — int, default 48
  round_deadline_at      — timestamp, nullable
  api_key_user_id        — user whose key pays for LLM; set at start

game_players
  character_slot_id      — nullable, references exposition.playable_characters[].id
  character_validated    — boolean, default false
  status                 — active | abandoned
  is_ai_controlled       — boolean, default false

exposition (JSONB extension)
  playable_characters      — array of { id, name, role, hook }

pending_actions
  round_number           — int
  forced_by_timeout      — boolean, default false
  UNIQUE (game_id, user_id, round_number)  — one slot per player per round
```

### Narrator methods (revised)

| Method | When called |
|--------|-------------|
| `generate_exposition(seed)` | Game start |
| `generate_playable_characters(exposition, player_drafts)` | Game start |
| `adapt_character(exposition, imported_character)` | Game start, for imports |
| `validate_character(exposition, slot, name, description)` | Slot claim |
| `adjudicate_action(story, exposition, character, action_text)` | **Each act submit** |
| `generate_ai_action(story, exposition, character)` | AI-controlled player round |
| `generate_dm_beat(story, accepted_actions)` | DM round |
| `evaluate_progress(story)` | DM round |

---

## Implementation cross-reference

Map flows to implementation order in BIG_CHANGE.md:

| Step | Flows covered |
|------|---------------|
| 2. Auth | Register, login, logout, session validation |
| 3. BYOK | API key add/remove, host onboarding |
| 4. Game lobby | Create, share, join, leave (lobby), character PATCH, import character |
| 5. Turn loop | Start, slot claim, submit action, immediate adjudication, AFK, DM round |
| 6. End conditions | Death, mission complete, ended read-only |
| 7. Export/import | Game export, game import, character export |

---

*Last updated: 2026-07-06. Review decisions in [Decisions log](#decisions-log) before implementation.*

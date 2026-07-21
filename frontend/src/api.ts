declare global {
  interface Window {
    __API_URL__: string;
  }
}

const API_URL = window.__API_URL__ || "http://localhost:8000";

export function getToken(): string | null {
  return sessionStorage.getItem("token");
}

export function setToken(token: string | null) {
  if (token) sessionStorage.setItem("token", token);
  else sessionStorage.removeItem("token");
}

function formatApiError(data: unknown, status: number): string {
  if (!data || typeof data !== "object") return `HTTP ${status}`;

  const body = data as Record<string, unknown>;
  const detail = body.detail ?? body.message;

  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object" && "msg" in item) {
          const err = item as { msg?: string; loc?: unknown[] };
          const loc = Array.isArray(err.loc) ? err.loc.filter((p) => p !== "body").join(".") : "";
          return loc ? `${loc}: ${err.msg}` : (err.msg ?? JSON.stringify(item));
        }
        return JSON.stringify(item);
      })
      .join("; ");
  }
  if (detail && typeof detail === "object") {
    if ("msg" in detail) return String((detail as { msg: unknown }).msg);
    return JSON.stringify(detail);
  }

  return `HTTP ${status}`;
}

async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> | undefined),
  };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(formatApiError(data, res.status));
  return data as T;
}

export const client = {
  register: (email: string, password: string, display_name: string) =>
    api<{ access_token: string }>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, display_name }),
    }),
  login: (email: string, password: string) =>
    api<{ access_token: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  logout: () => api<void>("/auth/logout", { method: "POST" }),
  me: () => api<{ id: string; email: string; display_name: string }>("/me"),
  listApiKeys: () =>
    api<Array<{ id: string; vendor: string; last_four: string }>>("/me/settings/api-keys"),
  createApiKey: (api_key: string) =>
    api<{ id: string }>("/me/settings/api-keys", {
      method: "POST",
      body: JSON.stringify({ vendor: "openai", api_key }),
    }),
  deleteApiKey: (id: string) =>
    api<void>(`/me/settings/api-keys/${id}`, { method: "DELETE" }),
  listCharacters: () => api<CharacterDetail[]>("/characters"),
  createCharacter: (name: string, description: string) =>
    api<CharacterDetail>("/characters", {
      method: "POST",
      body: JSON.stringify({ name, description }),
    }),
  deleteCharacter: (id: string) =>
    api<void>(`/characters/${id}`, { method: "DELETE" }),
  listGames: () =>
    api<Array<{ id: string; seed: string; status: string; phase: string }>>("/games"),
  createGame: (seed: string, api_key_id: string, character_id: string) =>
    api<GameDetail>("/games", {
      method: "POST",
      body: JSON.stringify({ seed, api_key_id, character_id }),
    }),
  getGame: (id: string) => api<GameDetail>(`/games/${id}`),
  joinGame: (id: string, character_id: string) =>
    api<GameDetail>(`/games/${id}/join`, {
      method: "POST",
      body: JSON.stringify({ character_id }),
    }),
  leaveGame: (id: string) => api<GameDetail>(`/games/${id}/leave`, { method: "POST" }),
  startGame: (id: string) => api<GameDetail>(`/games/${id}/start`, { method: "POST" }),
  submitAction: (id: string, action_type: "act" | "pass", action_text?: string) =>
    api<{ accepted: boolean; reason?: string; game: GameDetail }>(`/games/${id}/actions`, {
      method: "POST",
      body: JSON.stringify({ action_type, action_text }),
    }),
  retryResolution: (id: string) =>
    api<GameDetail>(`/games/${id}/retry-resolution`, { method: "POST" }),
};

export interface CharacterDetail {
  id: string;
  user_id: string;
  name: string;
  description: string;
  game_id?: string | null;
  is_alive: boolean;
  death_summary?: string | null;
}

export interface GameDetail {
  id: string;
  seed: string;
  status: string;
  phase: string;
  host_user_id: string;
  round_number: number;
  end_reason?: string;
  round_state: {
    status: string;
    error_message?: string;
    retryable?: boolean;
  };
  players: Array<{
    character_id: string;
    user_id: string;
    display_name?: string;
    name: string;
    description: string;
    is_alive: boolean;
    action_submitted: boolean;
  }>;
  exposition?: Record<string, unknown>;
  beats: Array<{
    round_number: number;
    narrator_text: string;
    actions: Array<{
      character_id: string;
      character_name: string;
      action_type: string;
      action_text?: string | null;
    }>;
  }>;
}

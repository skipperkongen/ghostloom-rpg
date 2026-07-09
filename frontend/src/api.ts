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
  if (!res.ok) throw new Error(data.detail || data.message || `HTTP ${res.status}`);
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
  listGames: () =>
    api<Array<{ id: string; seed: string; status: string; phase: string }>>("/games"),
  createGame: (seed: string, api_key_id: string) =>
    api<GameDetail>("/games", {
      method: "POST",
      body: JSON.stringify({ seed, api_key_id }),
    }),
  getGame: (id: string) => api<GameDetail>(`/games/${id}`),
  joinGame: (id: string) => api<GameDetail>(`/games/${id}/join`, { method: "POST" }),
  leaveGame: (id: string) => api<GameDetail>(`/games/${id}/leave`, { method: "POST" }),
  updateCharacter: (id: string, character_name: string, answers: Array<{ question_id: string; choice_id: string }>) =>
    api<GameDetail>(`/games/${id}/players/me`, {
      method: "PATCH",
      body: JSON.stringify({ character_name, answers }),
    }),
  startGame: (id: string) => api<GameDetail>(`/games/${id}/start`, { method: "POST" }),
  submitAction: (id: string, action_type: "act" | "pass", action_text?: string) =>
    api<{ accepted: boolean; reason?: string; game: GameDetail }>(`/games/${id}/actions`, {
      method: "POST",
      body: JSON.stringify({ action_type, action_text }),
    }),
  retryResolution: (id: string) =>
    api<GameDetail>(`/games/${id}/retry-resolution`, { method: "POST" }),
};

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
    user_id: string;
    display_name?: string;
    character_name?: string;
    is_alive: boolean;
    action_submitted: boolean;
    questionnaire_complete: boolean;
  }>;
  character_questionnaire?: {
    questions: Array<{
      id: string;
      text: string;
      choices: Array<{ id: string; label: string }>;
    }>;
  };
  exposition?: Record<string, unknown>;
  beats: Array<{ role: string; text: string; character_name?: string }>;
}

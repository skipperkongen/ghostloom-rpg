import { client, CharacterDetail, GameDetail, getToken, setToken } from "./api";

type View = "login" | "register" | "games" | "settings" | "characters" | "game";

let currentView: View = "login";
let currentGameId: string | null = null;
let pollTimer: number | null = null;
let me: { id: string; display_name: string } | null = null;

const app = document.getElementById("app")!;

function el(
  tag: string,
  attrs: Record<string, string | ((e: Event) => void)> = {},
  children: (Node | string)[] = [],
): HTMLElement {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "className") node.className = v as string;
    else if (k.startsWith("on") && typeof v === "function") node.addEventListener(k.slice(2).toLowerCase(), v);
    else if (typeof v === "string") node.setAttribute(k, v);
  }
  for (const child of children) node.append(typeof child === "string" ? document.createTextNode(child) : child);
  return node;
}

function showError(container: HTMLElement, msg: string) {
  const err = container.querySelector(".error");
  if (err) err.textContent = msg;
}

async function init() {
  if (getToken()) {
    try {
      me = await client.me();
      currentView = "games";
    } catch {
      setToken(null);
    }
  }
  render();
}

function render() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
  app.innerHTML = "";
  if (currentView === "login") renderLogin();
  else if (currentView === "register") renderRegister();
  else if (currentView === "settings") renderSettings();
  else if (currentView === "characters") renderCharacters();
  else if (currentView === "games") renderGames();
  else if (currentView === "game" && currentGameId) renderGame(currentGameId);
}

function renderNav(): HTMLElement {
  return el("nav", {}, [
    el("button", { onClick: () => { currentView = "games"; render(); } }, ["Games"]),
    el("button", { onClick: () => { currentView = "characters"; render(); } }, ["Characters"]),
    el("button", { onClick: () => { currentView = "settings"; render(); } }, ["Settings"]),
    el("button", { className: "secondary", onClick: async () => {
      try { await client.logout(); } catch { /* ignore */ }
      setToken(null);
      me = null;
      currentView = "login";
      render();
    }}, [`Logout (${me?.display_name || ""})`]),
  ]);
}

function renderLogin() {
  const card = el("div", { className: "card" });
  const err = el("div", { className: "error" });
  const email = el("input", { type: "email", placeholder: "Email" });
  const password = el("input", { type: "password", placeholder: "Password" });
  card.append(
    el("h1", {}, ["Ghostloom"]),
    el("p", { className: "muted" }, ["Sign in to play"]),
    err,
    el("label", {}, ["Email"]), email,
    el("label", {}, ["Password"]), password,
    el("button", { onClick: async () => {
      try {
        const res = await client.login((email as HTMLInputElement).value, (password as HTMLInputElement).value);
        setToken(res.access_token);
        me = await client.me();
        currentView = "games";
        render();
      } catch (e) { showError(card, (e as Error).message); }
    }}, ["Login"]),
    el("p", {}, ["No account? ", el("a", { href: "#", onClick: (e: Event) => { e.preventDefault(); currentView = "register"; render(); } }, ["Register"])]),
  );
  app.append(card);
}

function renderRegister() {
  const card = el("div", { className: "card" });
  const err = el("div", { className: "error" });
  const email = el("input", { type: "email" });
  const displayName = el("input", { type: "text", placeholder: "Display name" });
  const password = el("input", { type: "password" });
  card.append(
    el("h1", {}, ["Register"]),
    err,
    el("label", {}, ["Email"]), email,
    el("label", {}, ["Display name"]), displayName,
    el("label", {}, ["Password"]), password,
    el("button", { onClick: async () => {
      try {
        const res = await client.register(
          (email as HTMLInputElement).value,
          (password as HTMLInputElement).value,
          (displayName as HTMLInputElement).value,
        );
        setToken(res.access_token);
        me = await client.me();
        currentView = "games";
        render();
      } catch (e) { showError(card, (e as Error).message); }
    }}, ["Create account"]),
    el("button", { className: "secondary", onClick: () => { currentView = "login"; render(); } }, ["Back"]),
  );
  app.append(card);
}

async function renderSettings() {
  const card = el("div", { className: "card" });
  card.append(el("h2", {}, ["API Keys"]), renderNav());
  const err = el("div", { className: "error" });
  const keyInput = el("input", { type: "password", placeholder: "OpenAI API key" });
  const list = el("div");

  async function refresh() {
    list.innerHTML = "";
    const keys = await client.listApiKeys();
    for (const k of keys) {
      list.append(
        el("div", { className: "player-row" }, [
          el("span", {}, [`${k.vendor} ••••${k.last_four}`]),
          el("button", { className: "danger", onClick: async () => {
            await client.deleteApiKey(k.id);
            await refresh();
          }}, ["Delete"]),
        ]),
      );
    }
  }

  card.append(
    err, list,
    el("label", {}, ["Add OpenAI key"]), keyInput,
    el("button", { onClick: async () => {
      try {
        await client.createApiKey((keyInput as HTMLInputElement).value);
        (keyInput as HTMLInputElement).value = "";
        await refresh();
      } catch (e) { showError(card, (e as Error).message); }
    }}, ["Add key"]),
  );
  app.append(card);
  try { await refresh(); } catch (e) { showError(card, (e as Error).message); }
}

async function renderCharacters() {
  const card = el("div", { className: "card" });
  card.append(el("h2", {}, ["Characters"]), renderNav());
  const err = el("div", { className: "error" });
  const nameInput = el("input", { placeholder: "Name (max 32)" });
  const descInput = el("textarea", { rows: "4", placeholder: "Describe your character…" });
  const list = el("div");

  async function refresh() {
    list.innerHTML = "";
    const chars = await client.listCharacters();
    for (const c of chars) {
      const status = !c.is_alive ? "dead" : c.game_id ? "in game" : "available";
      list.append(
        el("div", { className: "player-row" }, [
          el("span", {}, [`${c.name} (${status}) — ${c.description.slice(0, 60)}`]),
          el("button", {
            className: "danger",
            onClick: async () => {
              try {
                await client.deleteCharacter(c.id);
                await refresh();
              } catch (e) { showError(card, (e as Error).message); }
            },
          }, ["Delete"]),
        ]),
      );
    }
  }

  card.append(
    err, list,
    el("h3", {}, ["Create character"]),
    el("label", {}, ["Name"]), nameInput,
    el("label", {}, ["Description"]), descInput,
    el("button", { onClick: async () => {
      try {
        await client.createCharacter(
          (nameInput as HTMLInputElement).value,
          (descInput as HTMLTextAreaElement).value,
        );
        (nameInput as HTMLInputElement).value = "";
        (descInput as HTMLTextAreaElement).value = "";
        await refresh();
      } catch (e) { showError(card, (e as Error).message); }
    }}, ["Create"]),
  );
  app.append(card);
  try { await refresh(); } catch (e) { showError(card, (e as Error).message); }
}

function availableCharacters(chars: CharacterDetail[]): CharacterDetail[] {
  return chars.filter((c) => c.is_alive && !c.game_id);
}

async function renderGames() {
  const card = el("div", { className: "card" });
  card.append(el("h2", {}, ["Your Games"]), renderNav());
  const err = el("div", { className: "error" });
  const seed = el("input", { placeholder: "Story seed" });
  const keySelect = el("select");
  const createCharSelect = el("select");
  const joinCharSelect = el("select");
  const list = el("div");
  const joinId = el("input", { placeholder: "Game ID to join" });

  async function refresh() {
    list.innerHTML = "";
    const games = await client.listGames();
    for (const g of games) {
      list.append(
        el("div", { className: "player-row" }, [
          el("span", {}, [`${g.seed.slice(0, 40)}… (${g.status}/${g.phase})`]),
          el("button", { onClick: () => { currentGameId = g.id; currentView = "game"; render(); } }, ["Open"]),
        ]),
      );
    }
    const keys = await client.listApiKeys();
    keySelect.innerHTML = "";
    for (const k of keys) {
      keySelect.append(el("option", { value: k.id }, [`openai ••••${k.last_four}`]));
    }
    const chars = availableCharacters(await client.listCharacters());
    createCharSelect.innerHTML = "";
    joinCharSelect.innerHTML = "";
    for (const c of chars) {
      createCharSelect.append(el("option", { value: c.id }, [c.name]));
      joinCharSelect.append(el("option", { value: c.id }, [c.name]));
    }
  }

  card.append(
    err, list,
    el("h3", {}, ["Create game"]),
    el("label", {}, ["Seed"]), seed,
    el("label", {}, ["API key"]), keySelect,
    el("label", {}, ["Character"]), createCharSelect,
    el("button", { onClick: async () => {
      try {
        const game = await client.createGame(
          (seed as HTMLInputElement).value,
          (keySelect as HTMLSelectElement).value,
          (createCharSelect as HTMLSelectElement).value,
        );
        currentGameId = game.id;
        currentView = "game";
        render();
      } catch (e) { showError(card, (e as Error).message); }
    }}, ["Create"]),
    el("h3", {}, ["Join game"]),
    joinId,
    el("label", {}, ["Character"]), joinCharSelect,
    el("button", { onClick: async () => {
      try {
        const game = await client.joinGame(
          (joinId as HTMLInputElement).value.trim(),
          (joinCharSelect as HTMLSelectElement).value,
        );
        currentGameId = game.id;
        currentView = "game";
        render();
      } catch (e) { showError(card, (e as Error).message); }
    }}, ["Join"]),
  );
  app.append(card);
  try { await refresh(); } catch (e) { showError(card, (e as Error).message); }
}

async function renderGame(gameId: string) {
  const card = el("div", { className: "card" });
  const err = el("div", { className: "error" });
  const content = el("div");

  async function refresh() {
    const game = await client.getGame(gameId);
    content.innerHTML = "";
    content.append(
      el("p", { className: "muted" }, [`Phase: ${game.phase} | Round: ${game.round_number} | Status: ${game.status}`]),
      el("h3", {}, ["Players"]),
    );
    const myPlayer = game.players.find((p) => p.user_id === me?.id);
    for (const p of game.players) {
      content.append(el("div", { className: "player-row" }, [
        el("span", {}, [`${p.name} ${p.is_alive ? "" : "(dead)"} ${p.action_submitted ? "✓" : ""}`]),
      ]));
    }

    if (game.phase === "lobby") {
      renderLobby(content, game, err);
    } else if (game.phase === "player_round" && myPlayer?.is_alive && !myPlayer.action_submitted) {
      renderActionForm(content, game, err);
    } else if (game.phase === "dm_round") {
      content.append(el("p", {}, ["DM is resolving the round…"]));
    } else if (game.phase === "resolution_failed") {
      content.append(el("p", { className: "error" }, [game.round_state.error_message || "Resolution failed"]));
      if (game.host_user_id === me?.id) {
        content.append(el("button", { onClick: async () => { await client.retryResolution(gameId); await refresh(); } }, ["Retry resolution"]));
      }
    }

    if (game.beats.length) {
      content.append(el("h3", {}, ["Story"]));
      for (const beat of game.beats) {
        content.append(el("div", { className: "beat round" }, [
          el("strong", {}, [`Round ${beat.round_number}`]),
        ]));
        for (const action of beat.actions) {
          const text = action.action_type === "pass"
            ? `${action.character_name} passes`
            : `${action.character_name}: ${action.action_text || ""}`;
          content.append(el("div", { className: "beat player" }, [text]));
        }
        content.append(el("div", { className: "beat narrator" }, [beat.narrator_text]));
      }
    }

    if (game.phase === "dm_round" || game.phase === "resolution_failed") {
      if (!pollTimer) pollTimer = window.setInterval(() => refresh().catch(() => {}), 2000);
    }
  }

  card.append(
    renderNav(),
    el("button", { className: "secondary", onClick: () => { currentView = "games"; render(); } }, ["← Back"]),
    el("h2", {}, ["Game"]),
    err, content,
    el("button", { className: "danger", onClick: async () => {
      try { await client.leaveGame(gameId); currentView = "games"; render(); }
      catch (e) { showError(card, (e as Error).message); }
    }}, ["Leave game"]),
  );
  app.append(card);
  try { await refresh(); } catch (e) { showError(card, (e as Error).message); }
}

function renderLobby(container: HTMLElement, game: GameDetail, errEl: Element) {
  for (const p of game.players) {
    container.append(el("p", { className: "muted" }, [`${p.name}: ${p.description.slice(0, 120)}`]));
  }
  if (game.host_user_id === me?.id) {
    container.append(el("button", { onClick: async () => {
      try { await client.startGame(game.id); location.reload(); }
      catch (e) { (errEl as HTMLElement).textContent = (e as Error).message; }
    }}, ["Start game"]));
  } else {
    container.append(el("p", {}, ["Waiting for host to start…"]));
  }
}

function renderActionForm(container: HTMLElement, game: GameDetail, errEl: Element) {
  const actionText = el("textarea", { rows: "3", placeholder: "What do you do?" });
  container.append(
    el("h3", {}, ["Your turn"]),
    actionText,
    el("button", { onClick: async () => {
      try {
        const res = await client.submitAction(game.id, "act", (actionText as HTMLTextAreaElement).value);
        if (!res.accepted) (errEl as HTMLElement).textContent = res.reason || "Action rejected";
        else location.reload();
      } catch (e) { (errEl as HTMLElement).textContent = (e as Error).message; }
    }}, ["Act"]),
    el("button", { className: "secondary", onClick: async () => {
      try { await client.submitAction(game.id, "pass"); location.reload(); }
      catch (e) { (errEl as HTMLElement).textContent = (e as Error).message; }
    }}, ["Pass"]),
  );
}

init();

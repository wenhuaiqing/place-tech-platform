// Carries their name because it was built for them. Says so, on every page.
export const DISCLAIMER = "Built for a job application. Not affiliated with or endorsed by Place Estate Agents; all data is synthetic.";

// Same origin in dev (Vite proxy) and in production (nginx sidecar).
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

// Open demo: any visitor can propose, decide and implement changes, acting as
// one of the demo people. The rules still refuse, and changes go back to the
// build whenever the site idles. VITE_PUBLIC_WRITES=false (with
// PUBLIC_WRITES=false on the server) makes every write need the token.
export const PUBLIC_WRITES = import.meta.env.VITE_PUBLIC_WRITES !== "false";

// Operator write token: open the site once with ?write_token=<value>; it is
// kept in sessionStorage, scrubbed from the URL, and sent as X-Write-Token.
// It allows resetting the demo and exempts the session from rate limits.
const TOKEN_KEY = "place_demo_write_token";
export const ACTOR_KEY = "place_demo_actor";

function captureTokenFromUrl() {
  try {
    const url = new URL(window.location.href);
    const token = url.searchParams.get("write_token");
    if (token) {
      sessionStorage.setItem(TOKEN_KEY, token);
      url.searchParams.delete("write_token");
      window.history.replaceState({}, "", url.pathname + url.search + url.hash);
    }
  } catch { /* storage blocked */ }
}
captureTokenFromUrl();

export function writeToken() {
  try { return sessionStorage.getItem(TOKEN_KEY) || ""; } catch { return ""; }
}

export function authHeaders() {
  const token = writeToken();
  return token ? { "X-Write-Token": token } : {};
}

// Who the visitor is acting as. Recorded on every write and used for
// separation of duties; never trusted as identity. A production build takes
// it from Entra ID.
export function actorName() {
  try { return sessionStorage.getItem(ACTOR_KEY) || "Platform lead"; } catch { return "Platform lead"; }
}

export function setActorName(name) {
  try { sessionStorage.setItem(ACTOR_KEY, name); } catch { /* storage blocked */ }
}

// Carries their name because it was built for them. Says so, on every page.
export const DISCLAIMER = "Built for a job application. Not affiliated with or endorsed by Place Estate Agents; all data is synthetic.";

// Same origin in dev (Vite proxy) and in production (nginx sidecar).
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

// The operator's token (open the site once with ?write_token=<value>; kept in
// sessionStorage, scrubbed from the URL) resets the demo and lifts the rate
// limits for a live walkthrough.
const TOKEN_KEY = "place_demo_write_token";

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

// Open demo: any visitor can use the work orders, acting as one of the demo
// roles. The rules still refuse, and changes go back to the build whenever the
// site idles.
export const PUBLIC_WRITES = import.meta.env.VITE_PUBLIC_WRITES !== "false";

const ACTOR_KEY = "place_demo_actor";

// Who the visitor is acting as. Recorded on every write and used for
// separation of duties; never trusted as identity. In production it comes
// from Entra ID.
export function actorName() {
  try { return sessionStorage.getItem(ACTOR_KEY) || "Property manager - Avery"; } catch { return "Property manager - Avery"; }
}

export function setActorName(name) {
  try { sessionStorage.setItem(ACTOR_KEY, name); } catch { /* storage blocked */ }
}

export function requestHeaders() {
  return { "X-Actor": actorName(), ...authHeaders() };
}

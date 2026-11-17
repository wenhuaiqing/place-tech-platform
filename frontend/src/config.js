// Carries their name because it was built for them. Says so, on every page.
export const DISCLAIMER = "Built for a job application. Not affiliated with or endorsed by Place Estate Agents; all data is synthetic.";

// Same origin in dev (Vite proxy) and in production (nginx sidecar).
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

// The reports are read-only. The operator's token (open the site once with
// ?write_token=<value>; kept in sessionStorage, scrubbed from the URL) only
// lifts the assistant's rate limit for a live walkthrough.
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

export const PUBLIC_WRITES = false;

export function actorName() {
  return "Visitor";
}

export function requestHeaders() {
  return { ...authHeaders() };
}

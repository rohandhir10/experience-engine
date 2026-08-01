// The Python engine's HTTP API (server/main.py). Local-only right now —
// this is just an env var so it's a one-line change, not a rewrite, once
// there's a real deployed backend to point at.
export const ENGINE_API_URL =
  process.env.AURA_ENGINE_API_URL || "http://localhost:8000";

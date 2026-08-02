// The Python engine's HTTP API (server/main.py), hosted on Railway as a
// persistent service — not Vercel serverless functions, which is why this
// is an external URL rather than a same-deployment route. Set
// AURA_ENGINE_API_URL in Vercel's project env vars to the Railway
// service's public domain once it has one (Railway Settings ->
// Networking -> Generate Domain; services aren't public by default).
export const ENGINE_API_URL =
  process.env.AURA_ENGINE_API_URL || "http://localhost:8000";

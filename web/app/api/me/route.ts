import { engineFetchAsUser } from "@/lib/engineFetch";

// Proxies to server/main.py's DELETE /api/me - the "right of erasure"
// half. Irreversible; the confirmation step lives in the UI
// (components/DangerZone.tsx requires typing the account's email), not
// here, since a route handler has no way to know a human meant it.
export async function DELETE() {
  return engineFetchAsUser("/api/me", { method: "DELETE" });
}

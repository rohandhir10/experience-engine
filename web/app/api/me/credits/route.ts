import { engineFetchAsUser } from "@/lib/engineFetch";

// Proxies to server/main.py's /api/me/credits - the real balance and
// ledger history (server/credits.py) backing the Billing/Usage
// dashboard pages. Unlike /api/me/adaptations, a signed-out request is
// a plain 401 here (engineFetchAsUser's own default) rather than a soft
// "signedIn: false" - there's no anonymous credit balance to show.
export async function GET() {
  return engineFetchAsUser("/api/me/credits");
}

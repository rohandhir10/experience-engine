import { NextRequest } from "next/server";
import { engineFetchAsUser } from "@/lib/engineFetch";

// Proxies to server/main.py's /api/me/api-keys (server/api_keys.py). POST
// returns the raw key exactly once - dashboard/settings/page.tsx must
// show it to the human immediately and never fetch or display it again.
export async function GET() {
  return engineFetchAsUser("/api/me/api-keys");
}

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => ({}));
  return engineFetchAsUser("/api/me/api-keys", {
    method: "POST",
    body: { name: String(body.name ?? "") },
  });
}

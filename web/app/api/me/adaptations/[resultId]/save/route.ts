import { NextRequest } from "next/server";
import { engineFetchAsUser } from "@/lib/engineFetch";

// Adds a result to the caller's history so it can be favorited or filed
// — the shared-link case, where they're looking at a song they never
// adapted themselves. Idempotent upstream.
export async function POST(
  _request: NextRequest,
  { params }: { params: { resultId: string } }
) {
  return engineFetchAsUser(
    `/api/me/adaptations/${encodeURIComponent(params.resultId)}/save`,
    { method: "POST" }
  );
}

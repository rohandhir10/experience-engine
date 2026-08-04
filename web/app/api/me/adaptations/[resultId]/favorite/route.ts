import { NextRequest } from "next/server";
import { engineFetchAsUser } from "@/lib/engineFetch";

// Toggles the favorite flag on one of the signed-in user's own history
// rows. The engine scopes the write by user id (server/accounts.py::
// set_favorite), so this route only has to prove WHO is asking - it
// never has to check ownership itself.
export async function POST(
  request: NextRequest,
  { params }: { params: { resultId: string } }
) {
  const body = await request.json().catch(() => ({}));
  return engineFetchAsUser(
    `/api/me/adaptations/${encodeURIComponent(params.resultId)}/favorite`,
    { method: "POST", body: { is_favorite: Boolean(body.isFavorite) } }
  );
}

import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/auth";
import { engineFetchAsUser } from "@/lib/engineFetch";

// The signed-in user's adaptation history, proxied from the engine
// (server/main.py::me_adaptations). Unlike the other /api/me/* routes
// this answers 200-with-signedIn:false for anonymous visitors instead of
// 401 - the dashboard renders a "sign in to keep history" prompt from
// it, so a signed-out visit is an expected state here, not an error.
// ?favoritesOnly / ?collectionId narrow the list; both filter in SQL
// upstream rather than being trimmed here.
export async function GET(request: NextRequest) {
  const session = await auth().catch(() => null);
  if (!session?.auraUserId) {
    return NextResponse.json({ adaptations: [], signedIn: false });
  }

  const params = request.nextUrl.searchParams;
  const query = new URLSearchParams({
    favorites_only: String(params.get("favoritesOnly") === "true"),
  });
  const collectionId = params.get("collectionId");
  if (collectionId) query.set("collection_id", collectionId);

  const response = await engineFetchAsUser(`/api/me/adaptations?${query}`);
  if (!response.ok) return response;
  const data = await response.json();
  return NextResponse.json({ ...data, signedIn: true });
}

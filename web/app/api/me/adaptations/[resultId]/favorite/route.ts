import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/auth";
import { ENGINE_API_URL } from "@/lib/api";

// Toggles the favorite flag on one of the signed-in user's own history
// rows. The engine scopes the write by user id (server/accounts.py::
// set_favorite), so this route only has to prove WHO is asking - it
// never has to check ownership itself.
export async function POST(
  request: NextRequest,
  { params }: { params: { resultId: string } }
) {
  const session = await auth().catch(() => null);
  if (!session?.auraUserId) {
    return NextResponse.json({ error: "Sign in to save favorites." }, { status: 401 });
  }
  const secret = process.env.AURA_INTERNAL_API_SECRET;
  if (!secret) {
    return NextResponse.json(
      { error: "Accounts are not configured on this deployment." },
      { status: 503 }
    );
  }

  const body = await request.json().catch(() => ({}));

  let upstream: Response;
  try {
    upstream = await fetch(
      `${ENGINE_API_URL}/api/me/adaptations/${encodeURIComponent(params.resultId)}/favorite`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Aura-Internal-Secret": secret,
          "X-Aura-User-Id": session.auraUserId,
        },
        body: JSON.stringify({ is_favorite: Boolean(body.isFavorite) }),
      }
    );
  } catch {
    return NextResponse.json(
      { error: "AURA is temporarily unreachable. Please try again in a few minutes." },
      { status: 502 }
    );
  }

  const data = await upstream.json().catch(() => ({}));
  return NextResponse.json(data, { status: upstream.status });
}

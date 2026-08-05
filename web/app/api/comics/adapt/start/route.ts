import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/auth";
import { ENGINE_API_URL } from "@/lib/api";

// Same identity-forwarding pattern as app/api/adapt/start/route.ts and
// app/api/comics/adapt/route.ts: forward the signed-in user's id (if
// any) alongside the internal secret, so server/main.py records this
// chapter in their history and charges the right account.
async function identityHeaders(): Promise<Record<string, string>> {
  const secret = process.env.CASTIA_INTERNAL_API_SECRET;
  if (!secret) return {};
  const session = await auth().catch(() => null);
  if (!session?.castiaUserId) return {};
  return {
    "X-Castia-Internal-Secret": secret,
    "X-Castia-User-Id": session.castiaUserId,
  };
}

// Unlike app/api/comics/adapt/route.ts (which has to fight a Vercel
// function's timeout for a big chapter), this returns almost
// immediately - the real engine run happens in a background thread on
// server/main.py's side (POST /api/comics/adapt/start), and the
// frontend polls GET /api/comics/adapt/jobs/[jobId] for the actual
// result. Same shape as app/api/adapt/start/route.ts's proxy.
export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => ({}));

  let upstream: Response;
  try {
    upstream = await fetch(`${ENGINE_API_URL}/api/comics/adapt/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...(await identityHeaders()) },
      body: JSON.stringify(body),
    });
  } catch {
    return NextResponse.json(
      { error: "CASTIA is temporarily unreachable. Please try again in a few minutes." },
      { status: 502 }
    );
  }

  const data = await upstream.json().catch(() => ({}));
  return NextResponse.json(data, { status: upstream.status });
}

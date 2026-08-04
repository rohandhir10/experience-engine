import { NextResponse } from "next/server";
import { auth } from "@/auth";
import { ENGINE_API_URL } from "@/lib/api";

// The signed-in user's adaptation history, proxied from the engine
// (server/main.py::me_adaptations). Session comes from the Auth.js JWT
// cookie; the internal secret is what lets the engine trust the user id
// this route forwards.
export async function GET() {
  const session = await auth().catch(() => null);
  if (!session?.auraUserId) {
    return NextResponse.json({ adaptations: [], signedIn: false });
  }
  const secret = process.env.AURA_INTERNAL_API_SECRET;
  if (!secret) {
    return NextResponse.json({ adaptations: [], signedIn: true });
  }

  let upstream: Response;
  try {
    upstream = await fetch(`${ENGINE_API_URL}/api/me/adaptations`, {
      headers: {
        "X-Aura-Internal-Secret": secret,
        "X-Aura-User-Id": session.auraUserId,
      },
      cache: "no-store",
    });
  } catch {
    return NextResponse.json(
      { error: "AURA is temporarily unreachable. Please try again in a few minutes." },
      { status: 502 }
    );
  }

  const data = await upstream.json().catch(() => ({}));
  if (!upstream.ok) {
    return NextResponse.json(data, { status: upstream.status });
  }
  return NextResponse.json({ ...data, signedIn: true });
}

import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/auth";
import { ENGINE_API_URL } from "@/lib/api";
import { clientIpHeaders } from "@/lib/clientIp";

// Same ceiling reasoning as app/api/adapt/route.ts: Chapter DNA plus one
// full Writers' Room run PER PANEL (see server/main.py's
// comics_adapt_endpoint docstring) routinely takes well past a few
// seconds — 60s is the max Vercel Hobby-plan functions allow. A chapter
// with many panels can still exceed even this; that's a known,
// disclosed limitation (no async job/poll pattern exists for this
// endpoint yet, unlike /api/adapt/start), not something this route
// papers over.
export const maxDuration = 60;

// Same pattern as app/api/adapt/start/route.ts's identityHeaders(): forward
// the signed-in user's id, if any, so server/main.py records this chapter
// in their history (medium="webtoons"). Degrades to anonymous, exactly
// like the music side, if signed out or the internal secret isn't set.
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

// Proxies to server/main.py's /api/comics/adapt (engine/chapter_dna.py +
// engine/comics_adapt.py). Same shape as app/api/adapt/route.ts's proxy.
export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => ({}));

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 55_000);

  let upstream: Response;
  try {
    upstream = await fetch(`${ENGINE_API_URL}/api/comics/adapt`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(await identityHeaders()),
        // After identityHeaders so both agree on the same secret
        // value; this pair is what lets the engine bucket quota by
        // the real visitor instead of by this server (lib/clientIp.ts).
        ...clientIpHeaders(request),
      },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
  } catch (err) {
    const timedOut = err instanceof Error && err.name === "AbortError";
    return NextResponse.json(
      {
        error: timedOut
          ? "This chapter is taking longer than usual to adapt. Please try again with fewer panels."
          : "CASTIA is temporarily unreachable. Please try again in a few minutes.",
      },
      { status: timedOut ? 504 : 502 }
    );
  } finally {
    clearTimeout(timeout);
  }

  const data = await upstream.json().catch(() => ({}));
  return NextResponse.json(data, { status: upstream.status });
}

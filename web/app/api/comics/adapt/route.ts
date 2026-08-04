import { NextRequest, NextResponse } from "next/server";
import { ENGINE_API_URL } from "@/lib/api";

// Same ceiling reasoning as app/api/adapt/route.ts: Chapter DNA plus one
// full Writers' Room run PER PANEL (see server/main.py's
// comics_adapt_endpoint docstring) routinely takes well past a few
// seconds — 60s is the max Vercel Hobby-plan functions allow. A chapter
// with many panels can still exceed even this; that's a known,
// disclosed limitation (no async job/poll pattern exists for this
// endpoint yet, unlike /api/adapt/start), not something this route
// papers over.
export const maxDuration = 60;

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
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
  } catch (err) {
    const timedOut = err instanceof Error && err.name === "AbortError";
    return NextResponse.json(
      {
        error: timedOut
          ? "This chapter is taking longer than usual to adapt. Please try again with fewer panels."
          : "AURA is temporarily unreachable. Please try again in a few minutes.",
      },
      { status: timedOut ? 504 : 502 }
    );
  } finally {
    clearTimeout(timeout);
  }

  const data = await upstream.json().catch(() => ({}));
  return NextResponse.json(data, { status: upstream.status });
}

import { NextRequest, NextResponse } from "next/server";
import { ENGINE_API_URL } from "@/lib/api";

// A full engine run (Song DNA -> Writers' Room -> Judge, several LLM
// calls) routinely takes well past Vercel's 10s default function
// timeout - this route was hitting that ceiling and getting killed
// mid-request, which is indistinguishable from a 502 to the caller.
// 60s is the max Hobby-plan functions allow; if runs still time out on
// slower songs, the fix is a paid plan's higher ceiling, not a bigger
// number here.
export const maxDuration = 60;

// Proxies to the real Python engine (server/main.py), hosted on Railway.
// This is the seam the whole frontend was built around: components only
// ever call fetch("/api/adapt") and know nothing about what's behind it.
export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => ({}));

  // Aborts a few seconds before Vercel's own maxDuration kill so this
  // route can return a clean, friendly JSON error - a raw platform
  // timeout looks identical to a crashed backend from the caller's side.
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 55_000);

  let upstream: Response;
  try {
    upstream = await fetch(`${ENGINE_API_URL}/api/adapt`, {
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
          ? "This song is taking longer than usual to adapt. Please try again."
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

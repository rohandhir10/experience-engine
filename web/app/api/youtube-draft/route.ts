import { NextRequest, NextResponse } from "next/server";
import { ENGINE_API_URL } from "@/lib/api";

// Transcript fetching is a single network call to YouTube, not a
// multi-agent engine run - nowhere near /api/adapt's 60s, but still
// worth a deliberate ceiling above Vercel's 10s default rather than
// leaving it to chance.
export const maxDuration = 30;

// Proxies to server/main.py's /api/youtube-draft (wraps
// engine/youtube_ingest.py). This route did not exist at all before -
// YoutubeImportField.tsx has always called fetch("/api/youtube-draft"),
// which 404'd against Next.js itself with no proxy route to catch it,
// so every "Fetch lyrics" click failed before ever reaching the Python
// backend. Mirrors app/api/adapt/route.ts's error-handling shape.
export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => ({}));

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 25_000);

  let upstream: Response;
  try {
    upstream = await fetch(`${ENGINE_API_URL}/api/youtube-draft`, {
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
          ? "Reading this video's captions is taking longer than usual. Please try again."
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

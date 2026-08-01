import { NextRequest, NextResponse } from "next/server";
import { ENGINE_API_URL } from "@/lib/api";

// Proxies to the real Python engine (server/main.py). This is the seam the
// whole frontend was built around: components only ever call
// fetch("/api/adapt") and know nothing about what's behind it.
export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => ({}));

  let upstream: Response;
  try {
    upstream = await fetch(`${ENGINE_API_URL}/api/adapt`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    return NextResponse.json(
      {
        error:
          "Can't reach the engine right now. Make sure it's running (uvicorn server.main:app --port 8000).",
      },
      { status: 502 }
    );
  }

  const data = await upstream.json().catch(() => ({}));
  return NextResponse.json(data, { status: upstream.status });
}

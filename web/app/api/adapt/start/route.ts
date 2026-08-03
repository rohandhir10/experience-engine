import { NextRequest, NextResponse } from "next/server";
import { ENGINE_API_URL } from "@/lib/api";

// Unlike /api/adapt/route.ts, this returns almost immediately - the real
// engine run happens in a background thread on server/main.py's side
// (Railway is a persistent process, not a serverless function, so it has
// no timeout ceiling to work around). This route only proxies the fast
// "did we already have this cached, or here's a job_id" response; the
// frontend polls /api/adapt/jobs/[jobId] for the actual result, which is
// what avoids Vercel's 60s Hobby-plan function ceiling for a full,
// multi-section song (see server/main.py's module docstring).
export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => ({}));

  let upstream: Response;
  try {
    upstream = await fetch(`${ENGINE_API_URL}/api/adapt/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    return NextResponse.json(
      { error: "AURA is temporarily unreachable. Please try again in a few minutes." },
      { status: 502 }
    );
  }

  const data = await upstream.json().catch(() => ({}));
  return NextResponse.json(data, { status: upstream.status });
}

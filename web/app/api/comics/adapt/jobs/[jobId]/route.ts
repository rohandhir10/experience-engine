import { NextRequest, NextResponse } from "next/server";
import { ENGINE_API_URL } from "@/lib/api";

// Polled repeatedly while a /api/comics/adapt/start job runs - same
// shape as app/api/adapt/jobs/[jobId]/route.ts, no AbortController/
// maxDuration handling needed since each call is a fast lookup on
// server/main.py's side (server/jobs.py).
export async function GET(
  _request: NextRequest,
  { params }: { params: { jobId: string } }
) {
  let upstream: Response;
  try {
    upstream = await fetch(`${ENGINE_API_URL}/api/comics/adapt/jobs/${params.jobId}`);
  } catch {
    return NextResponse.json(
      { error: "CASTIA is temporarily unreachable. Please try again in a few minutes." },
      { status: 502 }
    );
  }

  const data = await upstream.json().catch(() => ({}));
  return NextResponse.json(data, { status: upstream.status });
}

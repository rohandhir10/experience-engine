import { NextRequest, NextResponse } from "next/server";
import { ENGINE_API_URL } from "@/lib/api";

// Polled repeatedly by the frontend while a /api/adapt/start job runs -
// each call is a fast in-memory dict lookup on server/main.py's side, so
// this needs none of /api/adapt/route.ts's AbortController/maxDuration
// handling.
export async function GET(
  _request: NextRequest,
  { params }: { params: { jobId: string } }
) {
  let upstream: Response;
  try {
    upstream = await fetch(`${ENGINE_API_URL}/api/adapt/jobs/${params.jobId}`);
  } catch {
    return NextResponse.json(
      { error: "CASTIA is temporarily unreachable. Please try again in a few minutes." },
      { status: 502 }
    );
  }

  const data = await upstream.json().catch(() => ({}));
  return NextResponse.json(data, { status: upstream.status });
}

import { NextRequest, NextResponse } from "next/server";
import { ENGINE_API_URL } from "@/lib/api";

// Same proxy pattern as app/api/adapt/[id]/route.ts, for the comics
// share page's GET lookup (app/comics/s/[id]/page.tsx) against
// server/main.py's GET /api/comics/adapt/{result_id}.
export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  let upstream: Response;
  try {
    upstream = await fetch(`${ENGINE_API_URL}/api/comics/adapt/${params.id}`, {
      cache: "no-store",
    });
  } catch {
    return NextResponse.json(
      { error: "CASTIA is temporarily unreachable." },
      { status: 502 }
    );
  }

  const data = await upstream.json().catch(() => ({}));
  return NextResponse.json(data, { status: upstream.status });
}

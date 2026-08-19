import { NextRequest, NextResponse } from "next/server";
import { ENGINE_API_URL } from "@/lib/api";

// Same proxy pattern as app/api/comics/adapt/[id]/route.ts, against
// server/main.py's GET /api/comics/redraw/{result_id} - lets a previously
// computed redraw (server/cache.py::comics_redraw_content_id) be fetched
// again without re-running inpainting, the same way a song or chapter's
// result_id already can be.
export async function GET(request: NextRequest, props: { params: Promise<{ id: string }> }) {
  const params = await props.params;
  let upstream: Response;
  try {
    upstream = await fetch(`${ENGINE_API_URL}/api/comics/redraw/${params.id}`, {
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

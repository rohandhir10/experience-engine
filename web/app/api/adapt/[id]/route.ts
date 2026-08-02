import { NextRequest, NextResponse } from "next/server";
import { ENGINE_API_URL } from "@/lib/api";

// Same proxy pattern as the POST route above, for the share page's GET
// lookup. This exists (rather than having the client fetch Railway
// directly) so the browser only ever talks to this same-origin Next.js
// route — no CORS configuration and no NEXT_PUBLIC_ env var needed for
// what's otherwise a server-only URL.
export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  let upstream: Response;
  try {
    upstream = await fetch(`${ENGINE_API_URL}/api/adapt/${params.id}`, {
      cache: "no-store",
    });
  } catch {
    return NextResponse.json(
      { error: "AURA is temporarily unreachable." },
      { status: 502 }
    );
  }

  const data = await upstream.json().catch(() => ({}));
  return NextResponse.json(data, { status: upstream.status });
}

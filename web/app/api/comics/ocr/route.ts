import { NextRequest, NextResponse } from "next/server";
import { ENGINE_API_URL } from "@/lib/api";
import { clientIpHeaders } from "@/lib/clientIp";

// A single Cloud Vision call over one panel image, not a multi-agent
// engine call - same ceiling reasoning as app/api/youtube-draft/route.ts,
// well under /api/adapt's 60s but still worth a deliberate value.
export const maxDuration = 30;

// Proxies to server/main.py's /api/comics/ocr (wraps engine/comics_ocr.py,
// a Google Cloud Vision call). Re-packages the incoming multipart form
// rather than piping the raw request body through, since Next.js's
// fetch needs a real FormData/Blob to send a multipart request to the
// upstream engine.
export async function POST(request: NextRequest) {
  const incoming = await request.formData().catch(() => null);
  const image = incoming?.get("image");
  if (!(image instanceof Blob)) {
    return NextResponse.json({ error: "An image file is required." }, { status: 400 });
  }
  const language = incoming?.get("language");

  const upstreamForm = new FormData();
  upstreamForm.append("image", image, image instanceof File ? image.name : "panel.png");
  // Optional hint only - Cloud Vision auto-detects script/language per
  // block on its own, so omitting this entirely is the normal case.
  if (typeof language === "string" && language) {
    upstreamForm.append("language", language);
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 25_000);

  let upstream: Response;
  try {
    upstream = await fetch(`${ENGINE_API_URL}/api/comics/ocr`, {
      method: "POST",
      // No Content-Type: fetch sets the multipart boundary itself. The
      // client-IP pair is what lets the engine meter this per visitor -
      // one Cloud Vision call per panel is real money, and a sliced
      // chapter fires dozens of them (lib/clientIp.ts).
      headers: clientIpHeaders(request),
      body: upstreamForm,
      signal: controller.signal,
    });
  } catch (err) {
    const timedOut = err instanceof Error && err.name === "AbortError";
    return NextResponse.json(
      {
        error: timedOut
          ? "Reading this panel is taking longer than usual. Please try again."
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

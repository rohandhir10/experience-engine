import { NextRequest, NextResponse } from "next/server";
import { ENGINE_API_URL } from "@/lib/api";
import { clientIpHeaders } from "@/lib/clientIp";

// Image inpainting + text rendering (engine/comics_redraw.py) - not a
// multi-agent engine call, but still real per-pixel work; same
// deliberate ceiling as app/api/comics/ocr/route.ts, not /api/adapt's
// 60s.
export const maxDuration = 30;

// Proxies to server/main.py's /api/comics/redraw. Re-packages the
// incoming multipart form rather than piping the raw request body
// through, same reasoning as app/api/comics/ocr/route.ts.
export async function POST(request: NextRequest) {
  const incoming = await request.formData().catch(() => null);
  const image = incoming?.get("image");
  const regions = incoming?.get("regions");
  const defaultFont = incoming?.get("default_font");
  if (!(image instanceof Blob)) {
    return NextResponse.json({ error: "An image file is required." }, { status: 400 });
  }
  if (typeof regions !== "string") {
    return NextResponse.json({ error: "'regions' is required." }, { status: 400 });
  }

  const upstreamForm = new FormData();
  upstreamForm.append("image", image, image instanceof File ? image.name : "panel.png");
  upstreamForm.append("regions", regions);
  if (typeof defaultFont === "string") upstreamForm.append("default_font", defaultFont);

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 25_000);

  let upstream: Response;
  try {
    upstream = await fetch(`${ENGINE_API_URL}/api/comics/redraw`, {
      method: "POST",
      // No Content-Type: fetch sets the multipart boundary itself. The
      // client-IP pair is what lets the engine meter this per visitor -
      // inpainting is real per-pixel work, uncapped before this
      // (lib/clientIp.ts).
      headers: clientIpHeaders(request),
      body: upstreamForm,
      signal: controller.signal,
    });
  } catch (err) {
    const timedOut = err instanceof Error && err.name === "AbortError";
    return NextResponse.json(
      {
        error: timedOut
          ? "Redrawing this panel is taking longer than usual. Please try again."
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

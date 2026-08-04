import { NextRequest, NextResponse } from "next/server";
import { ENGINE_API_URL } from "@/lib/api";

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
  if (!(image instanceof Blob)) {
    return NextResponse.json({ error: "An image file is required." }, { status: 400 });
  }
  if (typeof regions !== "string") {
    return NextResponse.json({ error: "'regions' is required." }, { status: 400 });
  }

  const upstreamForm = new FormData();
  upstreamForm.append("image", image, image instanceof File ? image.name : "panel.png");
  upstreamForm.append("regions", regions);

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 25_000);

  let upstream: Response;
  try {
    upstream = await fetch(`${ENGINE_API_URL}/api/comics/redraw`, {
      method: "POST",
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

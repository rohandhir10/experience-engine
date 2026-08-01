import { NextRequest, NextResponse } from "next/server";
import { sampleResult } from "@/lib/sample-data";

// Placeholder endpoint. Real integration point: take `text` (or a YouTube
// draft, once reviewed) and run it through the Python engine — e.g. a
// small FastAPI service wrapping engine/pipeline.py, called from here.
// Right now this always returns the same sample result so the frontend
// has something real to render end-to-end while that wiring doesn't exist.
export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => ({}));
  const text = typeof body?.text === "string" ? body.text.trim() : "";

  if (!text) {
    return NextResponse.json({ error: "Paste a song first." }, { status: 400 });
  }

  await new Promise((resolve) => setTimeout(resolve, 900));

  return NextResponse.json(sampleResult);
}

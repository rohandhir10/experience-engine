import type { ComicPanel, OcrRegion } from "./comics-types";

export type RedrawRegionInput = {
  bbox: OcrRegion["bbox"];
  adaptedText: string;
};

export class RedrawRequestError extends Error {}

/** What a region's redraw text box actually shows, in priority order:
 * (1) the human's own typed override, (2) that region's real adapted
 * text from lib/comics-types.ts::panelToChapterBubbles's per-bubble
 * adaptation (regionAdaptedTexts), (3) - ONLY when there's exactly one
 * detected region AND it has no per-region result yet (an older run, or
 * a hand-typed panel that got a single region added after the fact) -
 * the panel's whole flat adaptedText, the one case that mapping is still
 * unambiguous. A multi-region panel with neither a per-region result nor
 * a human override shows an empty box rather than guessing. Pure and
 * pulled out of app/comics/page.tsx specifically so this rule has real
 * test coverage instead of only being checked by eye in the browser. */
export function resolveRedrawRegionText(
  panel: Pick<ComicPanel, "redrawRegionTexts" | "ocrRegions" | "adaptedText" | "regionAdaptedTexts">,
  index: number
): string {
  const override = panel.redrawRegionTexts?.[index];
  if (override != null) return override;
  const regionResult = panel.regionAdaptedTexts?.[index];
  if (regionResult != null) return regionResult;
  if (panel.ocrRegions?.length === 1) return panel.adaptedText;
  return "";
}

// Calls app/api/comics/redraw/route.ts, which proxies to
// server/main.py's /api/comics/redraw (engine/comics_redraw.py) - see
// that module's docstring for the honest scope: speech bubbles only
// (not SFX), one fixed bundled font that never matches the original
// lettering, a heuristic text-color guess. `regions` is only ever the
// subset the human has actually filled in (resolveRedrawRegionText
// above, now real per-bubble adaptation results by default, not a
// guess). Returns a data: URI, ready to drop into an <img> src or a
// download link - nothing is stored server-side, so there's no id to
// fetch this result by later.
export async function redrawPanel(
  file: File,
  regions: RedrawRegionInput[]
): Promise<string> {
  const form = new FormData();
  form.append("image", file, file.name);
  form.append(
    "regions",
    JSON.stringify(
      regions.map((r) => ({ bbox: r.bbox, adapted_text: r.adaptedText }))
    )
  );

  const res = await fetch("/api/comics/redraw", { method: "POST", body: form });
  const body = await res.json().catch(() => ({}));

  if (!res.ok) {
    throw new RedrawRequestError(body.error || body.detail || "Redrawing this panel failed.");
  }

  return `data:image/png;base64,${body.image_base64}`;
}

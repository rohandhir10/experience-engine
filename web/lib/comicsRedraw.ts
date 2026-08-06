import type { ComicPanel, OcrRegion } from "./comics-types";

export type RedrawRegionInput = {
  bbox: OcrRegion["bbox"];
  adaptedText: string;
  // A key into FONT_OPTIONS below, or undefined to fall back to the
  // request's defaultFont (redrawPanel's third argument) - lets one
  // bubble override the panel's default (a bolder font for one shout).
  font?: string;
};

// Must match engine/comics_redraw.py's FONTS keys exactly - server/main.py's
// comics_redraw_endpoint rejects any name not in that registry with a 400,
// so a mismatch here would surface as a real redraw failure, not a silent
// no-op. Every entry was fetched from Google Fonts' OFL-licensed source and
// its license checked before being bundled (engine/assets/fonts/*-OFL.txt).
export const FONT_OPTIONS: { value: string; label: string }[] = [
  { value: "comic-neue", label: "Comic Neue (default)" },
  { value: "patrick-hand", label: "Patrick Hand (casual/handwritten)" },
  { value: "liberation-sans", label: "Liberation Sans (plain)" },
];

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

export type RedrawResult = {
  dataUrl: string;
  // server/cache.py::comics_redraw_content_id - a real, content-addressed
  // id for this exact (image, regions) pair, the same idea as a song or
  // chapter's result_id. Identical inputs resolve to the same id and are
  // served from server-side cache rather than re-running inpainting -
  // see server/main.py's comics_redraw_endpoint docstring.
  id: string;
};

// Calls app/api/comics/redraw/route.ts, which proxies to
// server/main.py's /api/comics/redraw (engine/comics_redraw.py) - see
// that module's docstring for the honest scope: speech bubbles only
// (not SFX), a small curated set of bundled OFL comic fonts (FONT_OPTIONS
// above) rather than a match for the original lettering, a heuristic
// text-color guess. `regions` is only ever the subset the human has
// actually filled in (resolveRedrawRegionText above, now real per-bubble
// adaptation results by default, not a guess). `defaultFont` applies to
// any region that doesn't set its own `font`; omit both for the
// server's own default (Comic Neue). Returns a data: URI, ready to drop
// into an <img> src or a download link, plus the real id this result is
// cached under server-side - re-requesting the same (image, regions,
// fonts) is a cache hit, not a second inpainting run; changing only the
// font is correctly a cache MISS (server/cache.py::comics_redraw_content_id
// folds font choice into the id specifically so a font change can never
// silently serve back the old font's image).
export async function redrawPanel(
  file: File,
  regions: RedrawRegionInput[],
  defaultFont?: string
): Promise<RedrawResult> {
  const form = new FormData();
  form.append("image", file, file.name);
  form.append(
    "regions",
    JSON.stringify(
      regions.map((r) => ({ bbox: r.bbox, adapted_text: r.adaptedText, font: r.font ?? null }))
    )
  );
  if (defaultFont) form.append("default_font", defaultFont);

  const res = await fetch("/api/comics/redraw", { method: "POST", body: form });
  const body = await res.json().catch(() => ({}));

  if (!res.ok) {
    throw new RedrawRequestError(body.error || body.detail || "Redrawing this panel failed.");
  }

  return { dataUrl: `data:image/png;base64,${body.image_base64}`, id: body.id };
}

// A single chapter-slice image plus whatever script text has been drawn
// out of it so far. extractedText/adaptedText/why are plain user-
// editable fields regardless of source - "Run OCR" (lib/comicsOcr.ts)
// can pre-fill extractedText from a real Google Cloud Vision pass, but
// the field itself is always just text the human can freely overwrite,
// never locked to whatever OCR returned.
export type ComicPanel = {
  id: string;
  fileName: string;
  // The original File, kept so "Run OCR" can send the real image bytes
  // to /api/comics/ocr - not reconstructable from previewUrl alone.
  file: File;
  // A blob: URL for the file the user dropped in - never uploaded
  // anywhere except on an explicit "Run OCR" click, held only in this
  // tab's memory for the session.
  previewUrl: string;
  extractedText: string;
  // The flat, whole-panel adapted line and reason - the source of truth
  // ONLY for a panel with no detected regions (OCR never ran, pure
  // hand-typed dialogue), where there's no per-bubble structure to
  // adapt against. Once real regions exist, regionAdaptedTexts/
  // regionWhys below are what's actually used; see
  // lib/comics-types.ts::combinedAdaptedText for the one-block view
  // derived from them (CSV export, etc).
  adaptedText: string;
  why: string;
  ocrStatus: "idle" | "running" | "done" | "error";
  // Pixel-coordinate boxes (relative to the original image) from the
  // most recent successful OCR run - null until one has run. Cleared
  // whenever a new run starts, so a stale box never lingers over text
  // that's since changed.
  ocrRegions: OcrRegion[] | null;
  // Either a real caveat from the OCR pass itself (e.g. "confidence is
  // low") or a fetch/decoding failure message - always surfaced to the
  // human, never swallowed.
  ocrMessage: string | null;
  // Cloud Vision's own page-level script/language detection from the
  // most recent successful OCR run, most confident first - null until
  // one has run. This is the actual "no language picker needed" payoff
  // of Cloud Vision over the old Tesseract setup (see engine/
  // comics_ocr.py's docstring); lib/chapterLanguage.ts aggregates this
  // across every panel to guess the WHOLE CHAPTER's source language.
  detectedLanguages: DetectedLanguage[] | null;
  // Free-text name of who's speaking in this panel, typed by the human
  // reviewing it - null/empty means unattributed, and the DEFAULT voice
  // for every bubble in this panel that doesn't have its own detected
  // speaker (see panelToChapterBubbles - a region's own `speaker`, when
  // the optional vision-LLM pass named one, wins over this per-panel
  // fallback). Threaded through to engine.models.BubbleInput.voice,
  // which is what actually drives per-character voice consistency and
  // honorific-register tracking (engine/comics_adapt.py) - without this,
  // Chapter DNA generates per-character voice profiles that nothing
  // ever uses. Plain text, not a dropdown tied to a fixed roster: the
  // set of characters isn't known until Chapter DNA runs, and even then
  // a human should be free to name someone Chapter DNA didn't profile.
  voice: string | null;
  // Per-region adaptation results, parallel to ocrRegions - index i is
  // that region's own real adapted text/reason from the most recent
  // chapter-level adaptation run (panelToChapterBubbles sends one real
  // Writers' Room unit per detected region, not one flattened block per
  // panel), or null if that region hasn't been adapted yet. Null
  // (the whole array) until OCR has run at all; reset to an all-null
  // array matching the new region count whenever OCR reruns, same
  // "a stale box never lingers" rule ocrRegions/redrawRegionTexts
  // already follow.
  regionAdaptedTexts: (string | null)[] | null;
  regionWhys: (string | null)[] | null;
  // Per-region override text for "Redraw panel" (lib/comicsRedraw.ts),
  // parallel to ocrRegions - index i is the human-typed adapted text to
  // draw into ocrRegions[i]'s bbox, or null if they haven't filled that
  // region in yet. Defaults (when unfilled) to that region's own real
  // result in regionAdaptedTexts, once chapter adaptation has actually
  // run - see lib/comicsRedraw.ts::resolveRedrawRegionText. Null until
  // OCR has run; reset (to an all-null array matching the new region
  // count) whenever OCR reruns, same "a stale box never lingers" rule
  // ocrRegions itself already follows.
  redrawRegionTexts: (string | null)[] | null;
  // This panel's default font for "Redraw panel" - a key into
  // lib/comicsRedraw.ts::FONT_OPTIONS, or null to use the server's own
  // default (Comic Neue). Applies to every region except ones with their
  // own override in redrawRegionFonts below. Not reset when OCR reruns -
  // unlike region-indexed state, a font preference isn't tied to which
  // regions were detected.
  redrawFont: string | null;
  // Per-region font override, parallel to ocrRegions - index i overrides
  // redrawFont for that one region (a bolder font for one shout), or
  // null to use the panel's default. Null (the whole array) until OCR
  // has run; reset to an all-null array whenever OCR reruns, same
  // "a stale box never lingers" rule ocrRegions/redrawRegionTexts
  // already follow.
  redrawRegionFonts: (string | null)[] | null;
  // The composited PNG (as a data: URI) from the most recent successful
  // /api/comics/redraw call - null until one has run. This tab holds
  // only the data: URI, not persisted here across a reload, but the
  // underlying result IS cached server-side under redrawResultId below
  // (server/cache.py::comics_redraw_content_id) - re-running "Redraw
  // panel" with the same regions is a cache hit, not a second inpaint.
  // Not included in CSV export.
  redrawResultUrl: string | null;
  // The real, content-addressed id server/main.py cached this result
  // under (lib/comicsRedraw.ts::RedrawResult) - null until a redraw has
  // run. Fetchable later via GET /api/comics/redraw/{id}.
  redrawResultId: string | null;
  redrawStatus: "idle" | "running" | "error";
  redrawMessage: string | null;
};

export type OcrRegion = {
  text: string;
  bbox: { x: number; y: number; width: number; height: number };
  confidence: number;
  // Everything below is present only when the optional vision-LLM read
  // pass ran (engine/comics_vision.py, off unless CASTIA_VISION_READING
  // is set), so all of it is optional - a plain Cloud Vision result has
  // none of it and must keep working exactly as before.
  //
  // "llm" when a vision model's reading of this bubble was confidently
  // matched to this box and used; "vision" when it wasn't and Cloud
  // Vision's own text was kept. Never means "verified correct" - it
  // means "which system read it", and the human still reviews either way.
  textSource?: "llm" | "vision";
  // "dialogue" | "sfx" | "narration" | "background" | "unknown" - lets
  // sound effects and background signage be told apart from speech.
  kind?: string;
  // Who the model believes is speaking, or null when it wouldn't commit.
  // A null stays null: a wrong speaker silently corrupts character voice
  // for a whole chapter, so it is never guessed at downstream. Used by
  // panelToChapterBubbles as this region's own voice, ahead of the
  // panel-level fallback.
  speaker?: string | null;
};

export type DetectedLanguage = {
  languageCode: string;
  // Null when Vision detected a real script/language this project
  // doesn't have a human-readable name for yet (see engine/
  // comics_ocr.py's _LANGUAGE_NAMES) - the raw BCP-47 code is still
  // shown rather than hidden.
  languageName: string | null;
  confidence: number;
};

// Separates a panel id from a region index in a composite bubble id
// (panelToChapterBubbles/parseBubbleId below) - "::" rather than a
// character legal in a real panel id (file.name-derived ids can contain
// almost anything except this).
const REGION_ID_SEPARATOR = "::";

export type ChapterBubble = { id: string; text: string; voice?: string; kind?: string };

/** Builds one real adaptation unit ("bubble", in engine terms) per
 * detected OCR region for a panel that has them, instead of flattening
 * every region's text into a single block - the actual fix for a real
 * correctness problem: two characters speaking in the same panel used to
 * get concatenated and adapted as if it were one line, with no way to
 * tell which words belonged to which speaker, and no way to redraw them
 * back into their own separate bubbles with a real (not fabricated)
 * per-bubble result.
 *
 * A panel with no detected regions at all (OCR never ran - pure
 * hand-typed dialogue) still sends its whole extractedText as a single
 * unit, since there's no per-bubble structure to split against; a region
 * with only whitespace is dropped rather than sent as an empty bubble.
 *
 * Each bubble's voice prefers that specific region's own detected
 * speaker (only ever set by the optional vision-LLM read pass) over the
 * panel-level fallback - a real per-bubble signal beats a per-panel
 * guess when both exist.
 *
 * `kind`, when the optional vision-LLM read pass set one (OcrRegion.kind),
 * is threaded straight through to server/main.py's ComicsPanelText.kind
 * -> engine.models.BubbleInput.kind, which engine/comics_adapt.py uses
 * to skip the Writers' Room entirely for "sfx"/"background" regions -
 * see that module's _SKIP_KINDS for why. A flat whole-panel unit below
 * (no detected regions) never has a per-region kind, so it's always
 * undefined there, same as before this field existed.
 *
 * Region ids are `${panelId}::${regionIndex}`, parseable back apart by
 * parseBubbleId - this is how a result gets applied to the right
 * REGION instead of the whole panel once adaptation finishes
 * (applyBubbleResult below).
 */
export function panelToChapterBubbles(panel: ComicPanel): ChapterBubble[] {
  const regions = panel.ocrRegions;
  if (regions && regions.length > 0) {
    return regions
      .map((region, index) => ({
        id: `${panel.id}${REGION_ID_SEPARATOR}${index}`,
        text: region.text.trim(),
        voice: region.speaker?.trim() || panel.voice?.trim() || undefined,
        kind: region.kind,
      }))
      .filter((bubble) => bubble.text.length > 0);
  }
  if (panel.extractedText.trim()) {
    return [
      {
        id: panel.id,
        text: panel.extractedText,
        voice: panel.voice?.trim() || undefined,
      },
    ];
  }
  return [];
}

export type ParsedBubbleId = { panelId: string; regionIndex: number | null };

/** Inverse of panelToChapterBubbles's id scheme - `regionIndex: null`
 * means this bubble was the whole-panel flat unit (no detected regions),
 * not region 0 of a panel that has them. Anything that doesn't parse as
 * `panelId::N` is treated as a flat panel id - defensive against a
 * caller passing back an id this module didn't generate. */
export function parseBubbleId(id: string): ParsedBubbleId {
  const separatorIndex = id.lastIndexOf(REGION_ID_SEPARATOR);
  if (separatorIndex === -1) return { panelId: id, regionIndex: null };
  const regionIndex = Number(id.slice(separatorIndex + REGION_ID_SEPARATOR.length));
  if (!Number.isInteger(regionIndex) || regionIndex < 0) {
    return { panelId: id, regionIndex: null };
  }
  return { panelId: id.slice(0, separatorIndex), regionIndex };
}

/** Applies one bubble's real adaptation result to whichever panel (and,
 * for a multi-region panel, whichever REGION within it) the bubble id
 * actually names - returns the exact same panel object, unchanged, when
 * the id belongs to a different panel, so this composes directly into a
 * `setPanels(prev => prev.map(panel => applyBubbleResult(panel, id, result)))`
 * updater without an extra find/filter pass.
 *
 * Only pre-fills an empty slot, never overwrites text the human has
 * already reviewed/edited by hand - the same "pre-fill a draft, never
 * clobber a real edit" rule every OCR/adapt result in this workspace
 * already follows, now applied per-region instead of per-panel. */
export function applyBubbleResult(
  panel: ComicPanel,
  bubbleId: string,
  result: { adaptedText: string; why: string }
): ComicPanel {
  const parsed = parseBubbleId(bubbleId);
  if (parsed.panelId !== panel.id) return panel;

  if (parsed.regionIndex === null) {
    return {
      ...panel,
      adaptedText: panel.adaptedText.trim() ? panel.adaptedText : result.adaptedText,
      why: panel.why.trim() ? panel.why : result.why,
    };
  }

  const regionCount = panel.ocrRegions?.length ?? 0;
  if (parsed.regionIndex >= regionCount) return panel;

  const nextAdaptedTexts = [...(panel.regionAdaptedTexts ?? new Array(regionCount).fill(null))];
  const nextWhys = [...(panel.regionWhys ?? new Array(regionCount).fill(null))];
  const existing = nextAdaptedTexts[parsed.regionIndex];
  if (!existing || !existing.trim()) {
    nextAdaptedTexts[parsed.regionIndex] = result.adaptedText;
    nextWhys[parsed.regionIndex] = result.why;
  }
  return { ...panel, regionAdaptedTexts: nextAdaptedTexts, regionWhys: nextWhys };
}

/** One combined block of a panel's real per-region adapted text, in
 * region order - for CSV export and anywhere else that wants a single
 * string rather than per-bubble structure. Falls back to the flat
 * adaptedText field for a panel with no detected regions, which is
 * that field's real source of truth. */
export function combinedAdaptedText(panel: ComicPanel): string {
  if (panel.ocrRegions && panel.ocrRegions.length > 0) {
    return (panel.regionAdaptedTexts ?? [])
      .filter((text): text is string => !!text && text.trim().length > 0)
      .join("\n\n");
  }
  return panel.adaptedText;
}

/** combinedAdaptedText's counterpart for the "why" field - joined with
 * " / " rather than blank lines, since a why is normally one short
 * clause, not a paragraph. */
export function combinedWhy(panel: ComicPanel): string {
  if (panel.ocrRegions && panel.ocrRegions.length > 0) {
    return (panel.regionWhys ?? [])
      .filter((why): why is string => !!why && why.trim().length > 0)
      .join(" / ");
  }
  return panel.why;
}

export function panelToCsvRow(panel: ComicPanel, index: number): string {
  const cell = (value: string) => `"${value.replace(/"/g, '""')}"`;
  return [
    index + 1,
    panel.fileName,
    panel.voice ?? "",
    panel.extractedText,
    combinedAdaptedText(panel),
    combinedWhy(panel),
  ]
    .map((value) => cell(String(value)))
    .join(",");
}

export function panelsToCsv(panels: ComicPanel[]): string {
  const header = ["panel", "file_name", "voice", "extracted_text", "adapted_text", "why"].join(
    ","
  );
  return [header, ...panels.map((panel, index) => panelToCsvRow(panel, index))].join("\n");
}

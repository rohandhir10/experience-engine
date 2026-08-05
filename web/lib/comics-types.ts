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
  // reviewing it - null/empty means unattributed. Threaded straight
  // through to engine.models.BubbleInput.voice (lib/comicsAdapt.ts),
  // which is what actually drives per-character voice consistency and
  // honorific-register tracking (engine/comics_adapt.py) - without this,
  // Chapter DNA generates per-character voice profiles that nothing
  // ever uses. Plain text, not a dropdown tied to a fixed roster: the
  // set of characters isn't known until Chapter DNA runs, and even then
  // a human should be free to name someone Chapter DNA didn't profile.
  voice: string | null;
  // Per-region override text for "Redraw panel" (lib/comicsRedraw.ts),
  // parallel to ocrRegions - index i is the human-typed adapted text to
  // draw into ocrRegions[i]'s bbox, or null if they haven't filled that
  // region in yet. Deliberately NOT auto-filled by splitting
  // adaptedText across regions (there's no real per-bubble adaptation
  // yet - see engine/comics_adapt.py's known limitation - so any
  // auto-split would be a fabricated mapping). The one exception:
  // when there's exactly one region, the UI defaults an unfilled slot
  // to the panel's whole adaptedText, since that mapping IS
  // unambiguous. Null until OCR has run; reset (to an all-null array
  // matching the new region count) whenever OCR reruns, same "a stale
  // box never lingers" rule ocrRegions itself already follows.
  redrawRegionTexts: (string | null)[] | null;
  // The composited PNG (as a data: URI) from the most recent successful
  // /api/comics/redraw call - null until one has run. Not persisted
  // server-side (server/main.py's endpoint returns it, doesn't cache
  // it), not included in CSV export - purely this tab's in-memory
  // result, same as everything else about this workspace.
  redrawResultUrl: string | null;
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
  // for a whole chapter, so it is never guessed at downstream.
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

export function panelToCsvRow(panel: ComicPanel, index: number): string {
  const cell = (value: string) => `"${value.replace(/"/g, '""')}"`;
  return [
    index + 1,
    panel.fileName,
    panel.voice ?? "",
    panel.extractedText,
    panel.adaptedText,
    panel.why,
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

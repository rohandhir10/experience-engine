import type { DetectedLanguage, OcrRegion } from "./comics-types";
import { downscaleForOcr, rescaleRegions } from "./imageDownscale";

export type OcrResult = {
  regions: OcrRegion[];
  fullText: string;
  warning: string | null;
  detectedLanguages: DetectedLanguage[];
};

/** The single speaker to pre-fill a panel's "voice" field with, or null.
 *
 * A panel carries ONE voice field but can hold several bubbles, so this
 * only commits when the vision pass named exactly one distinct speaker
 * across the panel's dialogue. Two speakers in one panel is a real
 * conversation, and picking either one would attribute half the lines to
 * the wrong character - which is worse than leaving it blank, because
 * voice drives per-character consistency for the whole chapter
 * (engine/comics_adapt.py) and a wrong value corrupts it silently.
 */
export function resolvePanelSpeaker(regions: OcrRegion[]): string | null {
  const speakers = new Set(
    regions
      .filter((region) => region.kind === "dialogue")
      .map((region) => region.speaker?.trim())
      .filter((speaker): speaker is string => Boolean(speaker))
  );
  return speakers.size === 1 ? [...speakers][0] : null;
}

export class OcrRequestError extends Error {}

// Calls app/api/comics/ocr/route.ts, which proxies to server/main.py's
// /api/comics/ocr (engine/comics_ocr.py, a real Google Cloud Vision
// pass - see that module's docstring for what it can't do: stylized
// comic lettering can still come back wrong or garbled regardless of
// provider). `language` is optional and only ever a hint - Vision
// auto-detects script/language per block on its own, so no caller
// needs to pick one before running OCR. Always returns text for the
// caller to drop into an editable field, never applies it directly.
export async function runPanelOcr(file: File, language?: string): Promise<OcrResult> {
  // Uploads a downscaled copy when the panel is larger than OCR needs -
  // smaller upload, smaller payload, less for Vision to chew through.
  // The returned `scale` maps bboxes measured on that smaller image back
  // into the ORIGINAL image's pixel space, which is what every consumer
  // of these regions assumes (see lib/imageDownscale.ts::rescaleRegions).
  const { file: upload, scale } = await downscaleForOcr(file);

  const form = new FormData();
  form.append("image", upload, upload.name);
  if (language) form.append("language", language);

  const res = await fetch("/api/comics/ocr", { method: "POST", body: form });
  const body = await res.json().catch(() => ({}));

  if (!res.ok) {
    throw new OcrRequestError(body.error || body.detail || "OCR failed for this panel.");
  }

  const regions: OcrRegion[] = (body.regions ?? []).map(
    (region: Record<string, unknown>) => ({
      text: region.text as string,
      bbox: region.bbox as OcrRegion["bbox"],
      confidence: region.confidence as number,
      // Present only when the optional vision-LLM pass ran server-side.
      textSource: region.text_source as OcrRegion["textSource"],
      kind: region.kind as string | undefined,
      speaker: (region.speaker as string | null | undefined) ?? null,
    })
  );

  return {
    regions: rescaleRegions(regions, scale),
    fullText: body.full_text ?? "",
    warning: body.warning ?? null,
    detectedLanguages: (body.detected_languages ?? []).map(
      (lang: { language_code: string; language_name: string | null; confidence: number }) => ({
        languageCode: lang.language_code,
        languageName: lang.language_name,
        confidence: lang.confidence,
      })
    ),
  };
}

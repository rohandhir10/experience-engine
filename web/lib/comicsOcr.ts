import type { DetectedLanguage, OcrRegion } from "./comics-types";
import { downscaleForOcr, rescaleRegions } from "./imageDownscale";

export type OcrResult = {
  regions: OcrRegion[];
  fullText: string;
  warning: string | null;
  detectedLanguages: DetectedLanguage[];
};

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

  return {
    regions: rescaleRegions(body.regions ?? [], scale),
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

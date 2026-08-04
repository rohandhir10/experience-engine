import type { OcrRegion } from "./comics-types";

export type OcrResult = {
  regions: OcrRegion[];
  fullText: string;
  warning: string | null;
};

export class OcrRequestError extends Error {}

// Calls app/api/comics/ocr/route.ts, which proxies to server/main.py's
// /api/comics/ocr (engine/comics_ocr.py, a real Tesseract pass - see
// that module's docstring for what it can't do yet: stylized comic
// lettering and any language besides English). Always returns text for
// the caller to drop into an editable field, never applies it directly.
export async function runPanelOcr(file: File, language = "English"): Promise<OcrResult> {
  const form = new FormData();
  form.append("image", file, file.name);
  form.append("language", language);

  const res = await fetch("/api/comics/ocr", { method: "POST", body: form });
  const body = await res.json().catch(() => ({}));

  if (!res.ok) {
    throw new OcrRequestError(body.error || body.detail || "OCR failed for this panel.");
  }

  return {
    regions: body.regions ?? [],
    fullText: body.full_text ?? "",
    warning: body.warning ?? null,
  };
}

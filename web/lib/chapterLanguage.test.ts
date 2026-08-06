import { describe, expect, it } from "vitest";
import { guessChapterLanguage } from "./chapterLanguage";
import type { ComicPanel } from "./comics-types";

function panel(
  detectedLanguages: ComicPanel["detectedLanguages"],
  overrides: Partial<ComicPanel> = {}
): ComicPanel {
  return {
    id: Math.random().toString(),
    fileName: "panel.jpg",
    file: new File([], "panel.jpg"),
    previewUrl: "blob:mock",
    extractedText: "",
    adaptedText: "",
    why: "",
    ocrStatus: "idle",
    ocrRegions: null,
    ocrMessage: null,
    detectedLanguages,
    voice: null,
    regionAdaptedTexts: null,
    regionWhys: null,
    redrawRegionTexts: null,
    redrawResultUrl: null,
    redrawStatus: "idle",
    redrawMessage: null,
    ...overrides,
  };
}

describe("guessChapterLanguage", () => {
  it("returns null when no panel has been OCR'd yet", () => {
    expect(guessChapterLanguage([panel(null), panel(null)])).toBeNull();
  });

  it("picks the single detected language when only one panel has run OCR", () => {
    const result = guessChapterLanguage([
      panel([{ languageCode: "ko", languageName: "Korean", confidence: 92 }]),
      panel(null),
    ]);
    expect(result).toEqual({
      languageCode: "ko",
      languageName: "Korean",
      agreeingPanelCount: 1,
      ocrdPanelCount: 1,
    });
  });

  it("picks the majority language across multiple OCR'd panels", () => {
    const result = guessChapterLanguage([
      panel([{ languageCode: "ko", languageName: "Korean", confidence: 90 }]),
      panel([{ languageCode: "ko", languageName: "Korean", confidence: 88 }]),
      panel([{ languageCode: "en", languageName: "English", confidence: 70 }]),
    ]);
    expect(result?.languageCode).toBe("ko");
    expect(result?.agreeingPanelCount).toBe(2);
    expect(result?.ocrdPanelCount).toBe(3);
  });

  it("only considers each panel's own top-ranked detected language", () => {
    const result = guessChapterLanguage([
      panel([
        { languageCode: "ja", languageName: "Japanese", confidence: 60 },
        { languageCode: "en", languageName: "English", confidence: 95 },
      ]),
    ]);
    // Real-world data is already sorted most-confident-first by
    // engine/comics_ocr.py; this only reads index 0, not the max.
    expect(result?.languageCode).toBe("ja");
  });

  it("surfaces an unrecognized language's raw code with no name", () => {
    const result = guessChapterLanguage([panel([{ languageCode: "th", languageName: null, confidence: 80 }])]);
    expect(result).toEqual({
      languageCode: "th",
      languageName: null,
      agreeingPanelCount: 1,
      ocrdPanelCount: 1,
    });
  });

  it("ignores panels whose detectedLanguages array is empty", () => {
    const result = guessChapterLanguage([panel([]), panel([{ languageCode: "es", languageName: "Spanish", confidence: 85 }])]);
    expect(result?.languageCode).toBe("es");
    expect(result?.ocrdPanelCount).toBe(1);
  });
});

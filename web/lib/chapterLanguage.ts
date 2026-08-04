import type { ComicPanel } from "./comics-types";

export type ChapterLanguageGuess = {
  languageCode: string;
  languageName: string | null;
  // How many OCR'd panels' TOP-detected language agreed with this one -
  // out of all panels that have run OCR at least once, not out of the
  // whole chapter (an un-OCR'd panel has no vote either way).
  agreeingPanelCount: number;
  ocrdPanelCount: number;
};

/** Guesses a whole chapter's source language from each panel's own
 * Cloud Vision detection (engine/comics_ocr.py::_detected_languages) -
 * a plain majority vote over each OCR'd panel's single most-confident
 * detected language. This is a plain heuristic, not a real
 * chapter-level analysis: a chapter genuinely mixing two languages
 * (a loanword-heavy line, a bilingual gag) will still only ever report
 * one winner here. Returns null when no panel has been OCR'd yet -
 * there is nothing to guess from, and this never fabricates a "guess"
 * out of zero evidence.
 */
export function guessChapterLanguage(panels: ComicPanel[]): ChapterLanguageGuess | null {
  const votes = new Map<string, { languageName: string | null; count: number }>();
  let ocrdPanelCount = 0;

  for (const panel of panels) {
    const top = panel.detectedLanguages?.[0];
    if (!top) continue;
    ocrdPanelCount += 1;
    const existing = votes.get(top.languageCode);
    if (existing) {
      existing.count += 1;
    } else {
      votes.set(top.languageCode, { languageName: top.languageName, count: 1 });
    }
  }

  if (votes.size === 0) return null;

  let winner: [string, { languageName: string | null; count: number }] | null = null;
  for (const entry of votes.entries()) {
    if (!winner || entry[1].count > winner[1].count) winner = entry;
  }
  const [languageCode, { languageName, count }] = winner!;

  return { languageCode, languageName, agreeingPanelCount: count, ocrdPanelCount };
}

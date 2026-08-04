// Mirrors engine/models.py::SUPPORTED_LANGUAGES — the full roster, either
// side of a direction. Any two distinct languages from this list are a
// supported pairing now (full matrix, not a curated allow-list) -
// "supported" meaning the prompt layer runs, not that every pair has been
// quality-checked (see engine/models.py's comment on that distinction).
// Alphabetical after English (the default target) rather than any other
// order - this is a global, direction-agnostic tool, and an arbitrary
// non-alphabetical ordering reads as ranking one language/region above
// the others, which isn't a claim this list should make either way.
export const LANGUAGES = ["English", "Hindi", "Japanese", "Korean", "Spanish", "Urdu"] as const;

export type Language = (typeof LANGUAGES)[number];

// Kept for the homepage's "Adapt into" selector, which still only offers
// target - source defaults to auto-detect (target "English") or is
// picked explicitly (every other target) via a second selector that only
// appears once needed. See InputScreen.tsx.
export const TARGET_LANGUAGES = LANGUAGES;

export function sourceHintFor(targetLanguage: string, sourceLanguage: string): string {
  if (targetLanguage === "English") {
    return "Paste lyrics in Hindi, Japanese, Korean, Spanish, or Urdu — adapted into English, not translated.";
  }
  if (sourceLanguage === "English") {
    return `Paste English lyrics — adapted into ${targetLanguage}, not translated.`;
  }
  return `Paste ${sourceLanguage} lyrics — adapted into ${targetLanguage}, not translated.`;
}

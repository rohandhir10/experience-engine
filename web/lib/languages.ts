// Mirrors engine/models.py::SUPPORTED_TARGET_LANGUAGES — every direction
// AURA actually supports, not aspirational breadth. "English" is the
// original (and default) direction: Hindi/Korean/Japanese/Spanish source
// -> English. Selecting any other value here means the reverse: English
// source -> that language.
export const TARGET_LANGUAGES = ["English", "Hindi", "Korean", "Japanese", "Spanish"] as const;

export type TargetLanguage = (typeof TARGET_LANGUAGES)[number];

export function sourceHintFor(targetLanguage: string): string {
  if (targetLanguage === "English") {
    return "Paste lyrics in Hindi, Korean, Japanese, or Spanish — adapted into English, not translated.";
  }
  return `Paste English lyrics — adapted into ${targetLanguage}, not translated.`;
}

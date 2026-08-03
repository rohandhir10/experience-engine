// Best-effort, deterministic source-language detection for the pasted-lyrics
// box — no LLM call, no network round trip, so it can run on every
// keystroke. Scoped ONLY to engine/models.py::SUPPORTED_LANGUAGES (the
// LANGUAGES roster in ./languages), not general-purpose language ID: a
// script match unambiguously identifies Hindi/Urdu/Korean/Japanese among
// this roster (nothing else here shares Devanagari, Perso-Arabic, Hangul,
// or Han/Kana), and Latin-script text is disambiguated between English and
// Spanish only, since those are the only two Latin-script languages in the
// roster.
//
// Deliberately declines (returns null) rather than guessing when the
// signal is too thin — too little text, a script mix with no clear
// majority, or Latin-script text with no Spanish marker and no stopword
// signal either way. This only ever pre-fills the "From" selector; the
// user can always override it, so a wrong guess costs a click, but a
// confident-sounding wrong guess that's never noticed costs more.
import type { Language } from "./languages";

const MIN_CHARS_FOR_DETECTION = 8;
// A script must account for at least this fraction of the text's
// non-whitespace characters to count as "this language," so a couple of
// transliterated words or an emoji don't flip the whole guess.
const SCRIPT_MATCH_RATIO = 0.15;

const SCRIPT_PATTERNS: { language: Language; pattern: RegExp }[] = [
  { language: "Hindi", pattern: /[ऀ-ॿ]/gu },
  { language: "Urdu", pattern: /[؀-ۿݐ-ݿ]/gu },
  { language: "Korean", pattern: /[가-힣ᄀ-ᇿ]/gu },
  { language: "Japanese", pattern: /[぀-ヿ゠-ヿ一-鿿]/gu },
];

const SPANISH_MARKER_RE = /[ñáéíóúü¿¡]/i;

const SPANISH_STOPWORDS = new Set([
  "de", "la", "que", "el", "en", "y", "los", "del", "se", "las", "por",
  "un", "para", "con", "no", "una", "su", "al", "es", "lo", "como", "más",
  "pero", "sus", "le", "ya", "o", "este", "sí", "porque", "esta", "entre",
  "cuando", "muy", "sin", "sobre", "también", "me", "hasta", "hay", "donde",
  "quien", "desde", "todo", "nos", "durante", "todos", "uno", "les", "ni",
  "contra", "otros", "ese", "eso", "ante", "ellos", "e", "esto", "mí",
  "antes", "algunos", "qué", "unos", "yo", "otro", "otras", "otra", "él",
  "tanto", "esa", "estos", "mucho", "quienes", "nada", "muchos", "cual",
]);

const ENGLISH_STOPWORDS = new Set([
  "the", "and", "of", "to", "in", "is", "it", "you", "that", "he", "was",
  "for", "on", "are", "with", "as", "i", "his", "they", "be", "at", "one",
  "have", "this", "from", "or", "had", "by", "not", "what", "all", "were",
  "we", "when", "your", "can", "said", "there", "use", "an", "each",
  "which", "she", "do", "how", "their", "if", "will", "up", "other",
  "about", "out", "many", "then", "them", "these", "so", "some", "her",
  "would", "make", "like", "him", "into", "time", "has", "look", "two",
  "more", "my", "me", "no", "just",
]);

function scriptRatio(text: string, pattern: RegExp): number {
  const matches = text.match(pattern) ?? [];
  const nonSpaceLength = text.replace(/\s+/g, "").length || 1;
  return matches.length / nonSpaceLength;
}

export function detectSourceLanguage(text: string): Language | null {
  const trimmed = text.trim();
  if (trimmed.length < MIN_CHARS_FOR_DETECTION) return null;

  let bestLanguage: Language | null = null;
  let bestRatio = 0;
  for (const { language, pattern } of SCRIPT_PATTERNS) {
    const ratio = scriptRatio(trimmed, pattern);
    if (ratio > bestRatio) {
      bestRatio = ratio;
      bestLanguage = language;
    }
  }
  if (bestLanguage && bestRatio >= SCRIPT_MATCH_RATIO) {
    return bestLanguage;
  }

  // Latin-script text: English vs. Spanish only. An accented vowel, ñ, or
  // inverted punctuation is an unambiguous Spanish signal on its own.
  if (SPANISH_MARKER_RE.test(trimmed)) return "Spanish";

  const words = trimmed.toLowerCase().match(/\p{L}+/gu) ?? [];
  if (words.length < 4) return null;

  let spanishVotes = 0;
  let englishVotes = 0;
  for (const word of words) {
    if (SPANISH_STOPWORDS.has(word)) spanishVotes++;
    else if (ENGLISH_STOPWORDS.has(word)) englishVotes++;
  }
  if (spanishVotes === 0 && englishVotes === 0) return null;
  return spanishVotes > englishVotes ? "Spanish" : "English";
}

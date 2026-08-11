// Consumer-facing "why this section feels this way" note. Plan-based,
// not generative: this renders a fixed sentence template off two real,
// already-computed fields (SongDNA.poetic_register, song-level;
// SectionProfile.emotional_arc_point.dominant_feeling, per-section) -
// it never calls an LLM and never fills a gap with invented text. If
// dominantFeeling is missing (an older stored result, or a section
// name that didn't resolve - see server/mapping.py::_dominant_feeling),
// this renders nothing at all rather than a guess.
//
// poeticRegister is supposed to be a short label (engine/prompts.py's
// SONG_DNA_SYSTEM asks for one explicitly), but a model can still send a
// full descriptive sentence with its own reasoning attached - that breaks
// the "This song moves in a {X} register" template's grammar (seen in a
// real production run: "This song moves in a The song uses a Persianized
// Urdu register... register, and this section..."). isShortLabel is a
// cheap client-side guard, not a validator of correctness - it only
// decides which of two already-correct-content templates to use.
function isShortLabel(text: string): boolean {
  const trimmed = text.trim();
  const words = trimmed.split(/\s+/).filter(Boolean);
  return words.length <= 8 && !/[.!?]/.test(trimmed);
}

// "a intimate register" reads as a grammar error, not a content problem -
// a plain first-letter vowel check isn't linguistically perfect (silent h,
// "university"-style consonant sounds spelled with a vowel), but it's
// right for every label this field realistically produces, and a wrong
// guess here is cosmetic, not a fabricated claim about the song.
function indefiniteArticleFor(text: string): "a" | "an" {
  return /^[aeiou]/i.test(text.trim()) ? "an" : "a";
}

export function LoreStoryline({
  poeticRegister,
  dominantFeeling,
}: {
  // Pass this only once per song (e.g. on the first section) - it's a
  // song-level field, and repeating it under every section reads as
  // noise, not insight.
  poeticRegister?: string | null;
  dominantFeeling?: string | null;
}) {
  if (!dominantFeeling) return null;

  let sentence: string;
  if (!poeticRegister) {
    sentence = `This section carries a thread of ${dominantFeeling}.`;
  } else if (isShortLabel(poeticRegister)) {
    const article = indefiniteArticleFor(poeticRegister);
    sentence = `This song moves in ${article} ${poeticRegister} register, and this section carries a thread of ${dominantFeeling}.`;
  } else {
    // Too long/sentence-shaped to interpolate into the template above -
    // let it stand as its own sentence instead of mangling it.
    const withPeriod = /[.!?]$/.test(poeticRegister.trim())
      ? poeticRegister.trim()
      : `${poeticRegister.trim()}.`;
    sentence = `${withPeriod} This section carries a thread of ${dominantFeeling}.`;
  }

  return (
    <p className="mt-4 text-[12px] italic leading-relaxed text-ink/68 dark:text-ink-dark/68">
      {sentence}
    </p>
  );
}

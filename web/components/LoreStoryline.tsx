// Consumer-facing "why this section feels this way" note. Plan-based,
// not generative: this renders a fixed sentence template off two real,
// already-computed fields (SongDNA.poetic_register, song-level;
// SectionProfile.emotional_arc_point.dominant_feeling, per-section) -
// it never calls an LLM and never fills a gap with invented text. If
// dominantFeeling is missing (an older stored result, or a section
// name that didn't resolve - see server/mapping.py::_dominant_feeling),
// this renders nothing at all rather than a guess.
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

  return (
    <p className="mt-4 text-[12px] italic leading-relaxed text-ink/35 dark:text-ink-dark/35">
      {poeticRegister
        ? `This song moves in a ${poeticRegister} register, and this section carries a thread of ${dominantFeeling}.`
        : `This section carries a thread of ${dominantFeeling}.`}
    </p>
  );
}

export type Singability = {
  sourceCount: number;
  shippedCount: number;
  closeMatch: boolean;
};

export type SectionComparison = {
  id: string;
  literal: string;
  aura: string;
  why: string;
  singability?: Singability | null;
  // Only present when this result came from a YouTube draft AND the
  // section count survived review unchanged (server/main.py's adapt()
  // drops timing entirely otherwise, rather than sync to the wrong line).
  startSeconds?: number;
  endSeconds?: number;
};

export type OriginalSection = {
  id: string;
  text: string;
};

export type ExperienceResult = {
  id: string;
  hook: string;
  sourceLanguage: string;
  targetLanguage: string;
  sections: SectionComparison[];
  original: OriginalSection[];
  videoId?: string;
  // Song-level (a correlation across sections, not a per-line number) -
  // see engine/rhyme.py's module comment for exactly what this compares
  // (the Translator's anchor vs. the shipped line, English-target only).
  // null/undefined means "not computed," never a zero score.
  phonemeRepetitionSimilarity?: number | null;
};

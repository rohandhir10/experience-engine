export type Singability = {
  sourceCount: number;
  shippedCount: number;
  closeMatch: boolean;
};

// One fragment of the winning line that differs from the Translator's
// literal anchor (engine/models.py's Deviation, via server/mapping.py's
// _deviations_payload). Use fragmentOriginal/fragmentAdapted to position
// a consumer-facing underline - do NOT render `justification` verbatim
// in consumer copy, it's written for an engineer auditing a ruling, not
// a listener (same reason `why` below is LLM-paraphrased before
// shipping); reuse the section's own `why` sentence for that popup's
// prose instead. `justification` is for the Enterprise/audit surface.
export type DeviationFragment = {
  fragmentOriginal: string;
  fragmentAdapted: string;
  justification: string;
};

export type SectionComparison = {
  id: string;
  literal: string;
  aura: string;
  why: string;
  singability?: Singability | null;
  // SongDNA.sections[n].emotional_arc_point.dominant_feeling - real,
  // per-section field. null/undefined for a result stored before this
  // field existed, never a placeholder string.
  dominantFeeling?: string | null;
  // Fragment-level Burden-of-Change ledger for this section. Empty for
  // a section with no deviations from the literal anchor - never absent
  // outright on a fresh result, but treat missing the same as empty.
  deviations?: DeviationFragment[];
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
  // SongDNA.poetic_register - Tier 0 (LLM classification, not measured).
  // Song-level, not per-section: it's the same register for the whole
  // song. null/undefined for a result stored before this field existed.
  poeticRegister?: string | null;
};

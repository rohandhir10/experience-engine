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
};

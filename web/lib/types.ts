export type SectionComparison = {
  id: string;
  literal: string;
  aura: string;
  why: string;
};

export type OriginalSection = {
  id: string;
  text: string;
};

export type ExperienceResult = {
  id: string;
  hook: string;
  sourceLanguage: string;
  sections: SectionComparison[];
  original: OriginalSection[];
};

// Real comparison entries only — no system's output here is invented.
// A system with no output for a given entry is `null`, rendered as
// "not yet generated," never left blank or faked with placeholder text.
//
// Source of truth for generating more of these: `benchmark/systems.py` +
// `benchmark/cli.py` (`python -m benchmark.cli run --corpus examples
// --run-id <id>`) already runs AURA, a single-prompt GPT baseline, and
// Google Translate over the same corpus, on the same source text, in one
// command — see benchmark/README.md. Nothing here should be populated by
// hand-typing a guess at what another system would say.
//
// Fairness, per how this page should stay honest: same source text, same
// target language, same section, clearly labeled which system produced
// which text and under what prompt (see `methodologyNote` below) — never
// cherry-picked to only the sections where AURA looks best.

export type ComparisonSystemId = "google_translate" | "gpt_single" | "aura";

export type ComparisonSection = {
  id: string;
  source: string;
  systems: Partial<Record<ComparisonSystemId, string>>;
};

export type ComparisonEntry = {
  songId: string;
  title: string;
  sourceLanguage: string;
  sections: ComparisonSection[];
  /** How this specific entry's data was actually produced — shown on
   * the page so the comparison isn't just asserted as fair. */
  provenance: string;
};

export const SYSTEM_LABELS: Record<ComparisonSystemId, string> = {
  google_translate: "Google Translate",
  gpt_single: "GPT (single prompt)",
  aura: "AURA",
};

export const methodologyNote =
  "Same source text, same target language, run once per system, shown " +
  "in full — not cherry-picked to sections where AURA happens to look " +
  "best. gpt_single is a genuinely good single prompt asking for the " +
  "same thing AURA promises (preserve emotional impact, imagery, tone), " +
  "not a strawman literal-translation prompt — beating a weak comparison " +
  "would prove nothing.";

export const comparisonEntries: ComparisonEntry[] = [
  {
    songId: "sadda_haq",
    title: "Sadda Haq",
    sourceLanguage: "Hindi/Punjabi (Devanagari)",
    provenance:
      "AURA's output here is a real production run through the deployed " +
      "engine, not a cherry-picked or edited example. Google Translate and " +
      "the GPT single-prompt baseline for this exact text have not been " +
      "generated yet — see benchmark/README.md to produce them.",
    sections: [
      {
        id: "section_1",
        source:
          "तुम लोगो की, इस दुनिया में हर कदम पे इंसा गलत\n" +
          "मै सही समझ के जो भी कहु तुम कहते हो गलत\n" +
          "मै गलत हु फिर कौन सही फिर कौन सही\n" +
          "फिर कौन सही\n" +
          "मर्जी से जीने की भी मै क्या तुम सबको मै अर्जी दू\n" +
          "ओ ओ ओ\n" +
          "मतलब की तुम सबका मुझपे मुझसे भी ज्यादा हक़ है ओ ओ\n" +
          "सद्दा हक़, एथे रख",
        systems: {
          aura:
            "In a world like this, every step is judged as wrong. " +
            "Whatever I say, I'm told it's off the mark. If I'm wrong, " +
            "then who is right? Should I need permission to live my life " +
            "my way? Oh, oh, oh, does that mean you think you have more " +
            "say over me? Oh, oh. My right, right here.",
          // google_translate: not yet generated — deliberately absent,
          // not filled with a guess.
          // gpt_single: not yet generated — deliberately absent.
        },
      },
    ],
  },
];

// Single registry of every editorial/content page's real dates, used in
// three places that must never drift apart: sitemap.ts's per-page
// lastModified, each page's own Article/BlogPosting JSON-LD dateModified,
// and the "Updated <date>" line rendered on the page itself. A date here
// is only ever bumped when the page's actual visible content changes -
// see the biweekly refresh Routine (docs/CAPABILITY_MATRIX.md), which is
// the one process allowed to touch this file on a schedule rather than
// as a one-off edit.
export type ContentKind = "blog" | "compare" | "landing" | "glossary" | "guide";

export type ContentEntry = {
  slug: string;
  path: string;
  kind: ContentKind;
  title: string;
  description: string;
  publishedDate: string; // ISO date, the day this URL first went live
  updatedDate: string; // ISO date, the day its content was last substantively edited
};

export const CONTENT_REGISTRY: ContentEntry[] = [
  {
    slug: "why-literal-translation-breaks-song-lyrics",
    path: "/blog/why-literal-translation-breaks-song-lyrics",
    kind: "blog",
    title: "Why literal translation breaks song lyrics",
    description:
      "Rhyme, meter, and connotation don't survive a word-for-word pass. What translation research actually says about why lyrics need adaptation, not transcription.",
    publishedDate: "2026-08-05",
    updatedDate: "2026-08-05",
  },
  {
    slug: "why-bleu-score-cant-judge-creative-translation",
    path: "/blog/why-bleu-score-cant-judge-creative-translation",
    kind: "blog",
    title: "Why BLEU score can't judge creative translation",
    description:
      "Automated MT metrics were built to score literal accuracy. Here's what the research says about their blind spots, and why an LLM-as-judge step exists at all.",
    publishedDate: "2026-08-05",
    updatedDate: "2026-08-05",
  },
  {
    slug: "what-manga-localization-actually-costs",
    path: "/blog/what-manga-localization-actually-costs",
    kind: "blog",
    title: "What manga and webtoon localization actually costs",
    description:
      "Real industry rates for translation, typesetting, and lettering - and where an automated first pass fits next to a professional workflow, not instead of one.",
    publishedDate: "2026-08-05",
    updatedDate: "2026-08-05",
  },
  {
    slug: "what-transcreation-means",
    path: "/blog/what-transcreation-means",
    kind: "blog",
    title: "What \"transcreation\" means, and why it's not just translation",
    description:
      "The localization industry's own term for adapting intent and feeling rather than words - where it comes from, and how it applies past marketing copy.",
    publishedDate: "2026-08-05",
    updatedDate: "2026-08-05",
  },
  {
    slug: "google-translate",
    path: "/compare/google-translate",
    kind: "compare",
    title: "Castia vs. Google Translate for lyrics and dialogue",
    description:
      "What Google Translate is actually built to do, where that's the right tool, and where a literal neural MT pass isn't the same job as adapting a lyric or a character's voice.",
    publishedDate: "2026-08-05",
    updatedDate: "2026-08-06",
  },
  {
    slug: "deepl",
    path: "/compare/deepl",
    kind: "compare",
    title: "Castia vs. DeepL for lyrics and dialogue",
    description:
      "DeepL's neural MT is genuinely strong at document and sentence-level accuracy. Here's the specific, real gap between that and adapting a song or a comic panel.",
    publishedDate: "2026-08-05",
    updatedDate: "2026-08-06",
  },
  {
    slug: "chatgpt-prompt",
    path: "/compare/chatgpt-prompt",
    kind: "compare",
    title: "Castia vs. a single ChatGPT prompt",
    description:
      "\"Just ask ChatGPT to translate it creatively\" skips the part that makes a rewrite trustworthy: a verifiable anchor and a stated reason for every change.",
    publishedDate: "2026-08-05",
    updatedDate: "2026-08-06",
  },
  {
    slug: "lyrics-translation",
    path: "/lyrics-translation",
    kind: "landing",
    title: "Song lyric translation that keeps the feeling",
    description:
      "Translate or adapt song lyrics across six languages without flattening rhyme, rhythm, or idiom into a literal crib sheet.",
    publishedDate: "2026-08-05",
    updatedDate: "2026-08-06",
  },
  {
    slug: "manga-webtoon-translation",
    path: "/manga-webtoon-translation",
    kind: "landing",
    title: "Manga and webtoon translation with real OCR and redraw",
    description:
      "Upload panels, get dialogue adapted per character with a stated reason for every creative choice, plus optional lettering redraw and typeset.",
    publishedDate: "2026-08-05",
    updatedDate: "2026-08-06",
  },
  {
    slug: "how-it-works",
    path: "/how-it-works",
    kind: "guide",
    title: "How Castia's Writers' Room pipeline actually works",
    description:
      "The real mechanism behind every adaptation: a literal Translator anchor, five Creative Adapter rewrites, an automated verification pass, and a Judge that scores and explains the winner — for both music and comics.",
    publishedDate: "2026-08-05",
    updatedDate: "2026-08-06",
  },
  {
    slug: "pricing",
    path: "/pricing",
    kind: "guide",
    title: "Castia pricing",
    description:
      "Credit-based pricing for song and comic/webtoon adaptation - pay-as-you-go packs, a Creator subscription, and Studio/Enterprise plans. Billing isn't live yet.",
    publishedDate: "2026-08-05",
    updatedDate: "2026-08-06",
  },
  {
    slug: "glossary",
    path: "/glossary",
    kind: "glossary",
    title: "Localization and translation glossary",
    description:
      "Plain-language definitions of the terms that actually matter for judging translation and localization quality - transcreation, back-translation, LLM-as-a-judge, and more.",
    publishedDate: "2026-08-05",
    updatedDate: "2026-08-05",
  },
];

export function contentByPath(path: string): ContentEntry | undefined {
  return CONTENT_REGISTRY.find((entry) => entry.path === path);
}

export function contentByKind(kind: ContentKind): ContentEntry[] {
  return CONTENT_REGISTRY.filter((entry) => entry.kind === kind);
}

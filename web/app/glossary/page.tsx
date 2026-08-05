import { SiteHeader } from "@/components/SiteHeader";
import { Footer } from "@/components/Footer";
import { JsonLd } from "@/components/JsonLd";
import { BreadcrumbNav } from "@/components/BreadcrumbNav";
import Link from "next/link";
import { contentByPath } from "@/lib/content";
import { breadcrumbJsonLd, definedTermSetJsonLd } from "@/lib/schema";

const entry = contentByPath("/glossary")!;

export const metadata = {
  title: entry.title,
  description: entry.description,
  alternates: { canonical: "/glossary" },
};

// Ordinary, standard-usage definitions - not claims that need an external
// citation to be true, the way a stat or a quote would. Each one links
// back to the Castia page where that concept is actually load-bearing
// (docs/CAPABILITY_MATRIX.md is the deeper source for the AI-specific
// terms), so a reader who lands here from a search result has somewhere
// real to go next.
const TERMS: { term: string; slug: string; definition: string; related?: { label: string; href: string } }[] = [
  {
    term: "Translation",
    slug: "translation",
    definition:
      "Rendering the meaning of text from one language into another. On its own, the word says nothing about whether the result reads naturally, preserves tone, or fits a constraint like rhyme or a speech bubble's size - it just means the meaning crossed the language boundary.",
  },
  {
    term: "Localization",
    slug: "localization",
    definition:
      "Adapting a product or piece of content for a specific language and culture, going beyond translation to also handle things like date formats, units, currency, idiom, and cultural references. Localizing a comic includes redrawing lettering to fit a different script's shape, not just swapping the words inside it.",
    related: { label: "Manga & webtoon translation", href: "/manga-webtoon-translation" },
  },
  {
    term: "Transcreation",
    slug: "transcreation",
    definition:
      "A term from the localization industry for recreating a piece of content's intent, tone, and emotional effect in another language, rather than its literal words - accepting that a faithful translation and a faithful adaptation are sometimes different texts. Most closely associated with advertising and creative copy, but the same problem shows up anywhere meaning depends on rhythm, connotation, or wordplay - which is exactly the case for song lyrics and character dialogue.",
    related: { label: "What transcreation means", href: "/blog/what-transcreation-means" },
  },
  {
    term: "Back-translation",
    slug: "back-translation",
    definition:
      "Translating a translated text back into its original language, as a check on how much meaning survived the round trip. It's a useful sanity check but not a substitute for judging the target-language text on its own terms - a back-translation can look \"correct\" while the actual target-language line still reads awkwardly to a native speaker.",
  },
  {
    term: "Sense-for-sense vs. word-for-word translation",
    slug: "sense-for-sense-vs-word-for-word",
    definition:
      "Word-for-word (literal) translation maps each source word to a target-language equivalent in order; sense-for-sense translation renders the overall meaning of a phrase or sentence, reordering or substituting words freely to do it. The distinction goes back to classical translation theory (it's the same tension Cicero and St. Jerome wrote about) and it's the exact axis a literal MT engine and a creative rewrite sit on opposite ends of.",
    related: { label: "Why literal translation breaks song lyrics", href: "/blog/why-literal-translation-breaks-song-lyrics" },
  },
  {
    term: "Semantic drift",
    slug: "semantic-drift",
    definition:
      "When a rewrite's meaning gradually moves away from the source as successive changes are made, until the result no longer says what the original said - even if each individual change seemed reasonable. A rewrite step with nothing to check itself against has no way to notice this happening.",
  },
  {
    term: "LLM-as-a-judge",
    slug: "llm-as-a-judge",
    definition:
      "Using a large language model to score or rank other language-model outputs against a rubric, instead of (or alongside) a fixed automated metric or a human rater. It's an active area of MT and NLP evaluation research, and it's the mechanism behind Castia's own Judge stage - which scores five creative rewrites against a literal anchor translation and picks a winner with a stated reason, rather than shipping whichever rewrite a single call happened to produce.",
    related: { label: "How it works", href: "/how-it-works" },
  },
  {
    term: "Grounding",
    slug: "grounding",
    definition:
      "Anchoring a model's output to a verifiable reference so it can be checked, rather than trusting a generated result on its own. In Castia's pipeline, the Translator's literal anchor translation is the grounding the Judge checks every creative rewrite against - a rewrite that drifts too far from what the line actually says gets caught, instead of shipping silently.",
  },
  {
    term: "Machine translation (MT)",
    slug: "machine-translation",
    definition:
      "Automated translation of text by software rather than a human translator, ranging from older rule-based and statistical systems to today's neural MT engines (Google Translate, DeepL). Neural MT is generally optimized for fluent, accurate sentence-level translation - not for preserving rhyme, meter, or a character's voice, which are different objectives it isn't built to score.",
    related: { label: "Castia vs. Google Translate", href: "/compare/google-translate" },
  },
  {
    term: "Post-editing (MTPE)",
    slug: "post-editing",
    definition:
      "A human editor reviewing and correcting raw machine-translation output, rather than translating from scratch. It's the industry-standard way to combine MT's speed with human judgment, and it's the same relationship a Castia adaptation has with a professional localization pass on something high-stakes: a fast, reasoned-through first draft, reviewed by a human before it ships somewhere that matters.",
  },
  {
    term: "OCR (Optical Character Recognition)",
    slug: "ocr",
    definition:
      "Software that detects and reads text inside an image. Comic and webtoon localization needs it because dialogue lives inside speech bubbles baked into the artwork, not as separate text - Castia's comics pipeline runs Google Cloud Vision OCR on each panel to find and read that text before any adaptation happens.",
    related: { label: "Manga & webtoon translation", href: "/manga-webtoon-translation" },
  },
  {
    term: "Typesetting / lettering",
    slug: "typesetting",
    definition:
      "In comics, placing translated dialogue back into a panel's speech bubbles - sizing and wrapping text to fit, matching font and style, and (when the original lettering is baked into the art) erasing the old text and inpainting the background underneath it first. A professional letterer's job; Castia's optional redraw step automates the erase-and-relet part of it.",
  },
  {
    term: "Cultural adaptation",
    slug: "cultural-adaptation",
    definition:
      "Changing a reference, idiom, or convention so it lands the way it was meant to for a different culture's audience - a pun that only works in the source language, a food or festival reference with no equivalent, or an honorific that doesn't map cleanly onto another language's social register. Distinct from localization in the technical/product sense above, though the two are often discussed together.",
  },
];

export default function GlossaryPage() {
  const path = entry.path;
  const breadcrumb = breadcrumbJsonLd([
    { name: "Home", path: "/" },
    { name: "Glossary", path },
  ]);
  const definedTermSet = definedTermSetJsonLd({
    path,
    name: entry.title,
    description: entry.description,
    terms: TERMS.map((t) => ({ term: t.term, definition: t.definition })),
  });

  return (
    <main className="min-h-screen px-6 pb-28 pt-8 sm:px-10">
      <JsonLd data={breadcrumb} />
      <JsonLd data={definedTermSet} />
      <div className="mx-auto max-w-3xl">
        <SiteHeader />

        <div className="mt-10">
          <BreadcrumbNav items={[{ name: "Home", path: "/" }, { name: "Glossary" }]} />
          <h1 className="mt-3 font-serif text-3xl text-ink dark:text-ink-dark sm:text-4xl">
            Localization &amp; translation glossary.
          </h1>
          <p className="mt-4 max-w-prose text-[15px] leading-relaxed text-ink/55 dark:text-ink-dark/55">
            The terms that actually matter for judging whether a
            translation or adaptation is good - not a marketing glossary,
            the working vocabulary behind{" "}
            <Link href="/how-it-works" className="underline decoration-ink/20 underline-offset-4">
              how Castia works
            </Link>
            .
          </p>
        </div>

        <div className="mt-12 space-y-10">
          {TERMS.map((t) => (
            <div key={t.slug} id={t.slug} className="scroll-mt-24 border-b border-black/[0.06] pb-8 dark:border-white/[0.07]">
              <h2 className="font-serif text-lg text-ink dark:text-ink-dark">{t.term}</h2>
              <p className="mt-2.5 max-w-prose text-[14px] leading-relaxed text-ink/60 dark:text-ink-dark/60">
                {t.definition}
              </p>
              {t.related && (
                <Link
                  href={t.related.href}
                  className="mt-2.5 inline-block text-[13px] underline decoration-ink/20 underline-offset-4 text-ink/50 hover:text-ink/75 dark:text-ink-dark/50 dark:hover:text-ink-dark/75"
                >
                  {t.related.label} →
                </Link>
              )}
            </div>
          ))}
        </div>

        <Footer />
      </div>
    </main>
  );
}

import { SiteHeader } from "@/components/SiteHeader";
import { Footer } from "@/components/Footer";
import { JsonLd } from "@/components/JsonLd";
import { BreadcrumbNav } from "@/components/BreadcrumbNav";
import { SourceList } from "@/components/SourceList";
import { ScreenshotSlot } from "@/components/ScreenshotSlot";
import { CompareDiagram } from "@/components/CompareDiagram";
import Link from "next/link";
import { contentByPath } from "@/lib/content";
import { breadcrumbJsonLd, articleJsonLd } from "@/lib/schema";

const entry = contentByPath("/compare/deepl")!;

export const metadata = {
  title: entry.title,
  description: entry.description,
  alternates: { canonical: entry.path },
};

const SOURCES = [
  {
    name: "DeepL, \"How does DeepL work?\" (DeepL's own blog)",
    url: "https://www.deepl.com/en/blog/how-does-deepl-work",
    note: "DeepL's own description of its neural MT architecture",
  },
  {
    name: "Zheng et al., \"Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena\" (NeurIPS 2023)",
    url: "https://arxiv.org/abs/2306.05685",
    note: "on using an LLM to score/rank model outputs against a rubric",
  },
  {
    name: "Low, P., \"Singable Translations of Songs\" (2003), Perspectives: Studies in Translatology",
    url: "https://www.tandfonline.com/doi/abs/10.1080/0907676X.2003.9961466",
  },
];

export default function CompareDeepLPage() {
  const breadcrumb = breadcrumbJsonLd([
    { name: "Home", path: "/" },
    { name: "Compare", path: "/compare/deepl" },
    { name: "DeepL" },
  ]);
  const article = articleJsonLd({
    path: entry.path,
    headline: entry.title,
    description: entry.description,
    publishedDate: entry.publishedDate,
    updatedDate: entry.updatedDate,
    citations: SOURCES,
  });

  return (
    <main className="min-h-screen px-6 pb-28 pt-8 sm:px-10">
      <JsonLd data={breadcrumb} />
      <JsonLd data={article} />
      <div className="mx-auto max-w-3xl">
        <SiteHeader />

        <div className="mt-10 grid grid-cols-1 gap-10 lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
          <div>
            <BreadcrumbNav items={[{ name: "Home", path: "/" }, { name: "Compare", path: "/compare/deepl" }, { name: "DeepL" }]} />
            <h1 className="mt-3 font-serif text-3xl text-ink dark:text-ink-dark sm:text-4xl">
              Castia vs. DeepL.
            </h1>
            <p className="mt-4 max-w-prose text-[15px] leading-relaxed text-ink/55 dark:text-ink-dark/55">
              DeepL has a real, earned reputation for fluent, context-aware
              translation. That reputation is built on a different problem
              than the one Castia is built to solve.
            </p>
          </div>
          <CompareDiagram competitorName="DeepL" competitorStep="Whole-sentence neural pass" />
        </div>

        <section className="mt-12">
          <h2 className="font-serif text-xl text-ink dark:text-ink-dark">
            What DeepL actually does
          </h2>
          <p className="mt-3 max-w-prose text-[14px] leading-relaxed text-ink/60 dark:text-ink-dark/60">
            By DeepL's own description of its technology, it translates
            using neural network architectures - the company describes
            combining a neural MT engine with a specialized large language
            model, evaluating whole sentences for context rather than
            translating word-by-word. That contextual, whole-sentence
            approach is a real strength over older phrase-based systems, and
            it's a large part of why DeepL is widely regarded as producing
            more natural sentence-level output than earlier machine
            translation.
          </p>
          <p className="mt-3 max-w-prose text-[14px] leading-relaxed text-ink/60 dark:text-ink-dark/60">
            What DeepL's own published description doesn't include is a
            step where the system generates multiple differently-angled
            drafts of a line and has a separate stage score them against a
            rubric before choosing one - it's built to produce one strong
            translation per request, which is the right shape for the
            documents and general text it's aimed at.
          </p>
        </section>

        <section className="mt-12">
          <h2 className="font-serif text-xl text-ink dark:text-ink-dark">
            Why a lyric or a character's line needs more than one draft
          </h2>
          <p className="mt-3 max-w-prose text-[14px] leading-relaxed text-ink/60 dark:text-ink-dark/60">
            A single, even very fluent, translation of a lyric still has to
            make a choice: keep the literal meaning, or bend it to preserve
            rhyme and rhythm. Peter Low's "Pentathlon Principle" treats that
            as an unavoidable tradeoff between five demands (singability,
            sense, naturalness, rhythm, rhyme) rather than something one
            correct answer resolves. Castia's Creative Adapter stage exists
            to actually make that tradeoff on purpose, five different ways,
            instead of settling on whichever balance one pass happened to
            land on.
          </p>
          <p className="mt-3 max-w-prose text-[14px] leading-relaxed text-ink/60 dark:text-ink-dark/60">
            And because a creative rewrite can drift from what a line
            actually means if nothing checks it, Castia's Judge stage scores
            every rewrite against a literal anchor translation before
            picking one - the same "have a model score candidate outputs
            against a rubric" approach NeurIPS 2023 research on
            LLM-as-a-judge evaluation found can track human preference
            well, while also documenting real biases (verbosity, position)
            that a judge design has to account for rather than assume away.
          </p>
        </section>

        <section className="mt-12">
          <h2 className="font-serif text-xl text-ink dark:text-ink-dark">
            Side by side
          </h2>
          <div className="mt-5 overflow-x-auto rounded-2xl border border-black/[0.10] dark:border-white/[0.11]">
            <table className="w-full min-w-[480px] text-left text-[13px]">
              <thead>
                <tr className="border-b border-black/[0.10] dark:border-white/[0.11]">
                  <th className="p-4 font-medium text-ink/50 dark:text-ink-dark/50"> </th>
                  <th className="p-4 font-medium text-ink dark:text-ink-dark">DeepL</th>
                  <th className="p-4 font-medium text-ink dark:text-ink-dark">Castia</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-black/[0.10] dark:divide-white/[0.11]">
                {[
                  ["Best for", "Documents, business text, general fluent translation", "Song lyrics and comic dialogue that need to keep their feeling"],
                  ["Context handling", "Whole-sentence, per DeepL's own description", "Whole-song / whole-chapter (Chapter DNA cast & tone profile for comics)"],
                  ["How many drafts per line", "One", "Six (one literal anchor + five creative rewrites)"],
                  ["Verification step", "Not documented", "A Judge scores every rewrite against the literal anchor"],
                  ["Explains its changes", "No", "Every departure from literal ships with a stated reason"],
                ].map(([label, dl, castia]) => (
                  <tr key={label}>
                    <td className="p-4 text-ink/50 dark:text-ink-dark/50">{label}</td>
                    <td className="p-4 text-ink/70 dark:text-ink-dark/70">{dl}</td>
                    <td className="p-4 text-ink/70 dark:text-ink-dark/70">{castia}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="mt-14">
          <h2 className="font-serif text-xl text-ink dark:text-ink-dark">
            Same line, run through both
          </h2>
          <p className="mt-3 max-w-prose text-[14px] leading-relaxed text-ink/60 dark:text-ink-dark/60">
            One source line, the same input, run through DeepL and through
            Castia. Unedited output, side by side.
          </p>
          <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <ScreenshotSlot label="DeepL" path="/screenshots/compare/deepl.png" />
            <ScreenshotSlot label="Castia" path="/screenshots/compare/deepl-castia.png" />
          </div>
        </section>

        <div className="mt-14 rounded-2xl bg-[#181310] p-8 text-center sm:p-10">
          <p className="font-serif text-xl text-white sm:text-2xl">
            See what whole-song context catches.
          </p>
          <p className="mt-2 max-w-md mx-auto text-[13px] leading-relaxed text-white/50">
            Paste a verse and see the literal anchor, all five rewrites, and
            the Judge's stated reasoning for the one it picked.
          </p>
          <Link
            href="/music"
            className="mt-6 inline-block rounded-full bg-white px-6 py-2.5 text-[13px] font-medium text-black transition active:scale-[0.97]"
          >
            Try it on a lyric
          </Link>
        </div>

        <p className="mt-8 max-w-prose text-[13px] leading-relaxed text-ink/45 dark:text-ink-dark/45">
          Also see{" "}
          <Link href="/compare/google-translate" className="underline decoration-ink/20 underline-offset-4">
            Castia vs. Google Translate
          </Link>{" "}
          and{" "}
          <Link href="/compare/chatgpt-prompt" className="underline decoration-ink/20 underline-offset-4">
            Castia vs. a single ChatGPT prompt
          </Link>
          .
        </p>

        <SourceList sources={SOURCES} />

        <Footer />
      </div>
    </main>
  );
}

import { SiteHeader } from "@/components/SiteHeader";
import { Footer } from "@/components/Footer";
import { JsonLd } from "@/components/JsonLd";
import { BreadcrumbNav } from "@/components/BreadcrumbNav";
import { SourceList } from "@/components/SourceList";
import { CompareDiagram } from "@/components/CompareDiagram";
import Link from "next/link";
import { contentByPath } from "@/lib/content";
import { breadcrumbJsonLd, articleJsonLd } from "@/lib/schema";

const entry = contentByPath("/compare/chatgpt-prompt")!;

export const metadata = {
  title: entry.title,
  description: entry.description,
  alternates: { canonical: entry.path },
};

const SOURCES = [
  {
    name: "Zheng et al., \"Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena\" (NeurIPS 2023)",
    url: "https://arxiv.org/abs/2306.05685",
    note: "strong LLM judges can match human preference well, but carry documented biases (verbosity, position, self-enhancement)",
  },
  {
    name: "Callison-Burch, Osborne & Koehn, \"Re-evaluating the Role of BLEU in Machine Translation Research\" (EACL 2006)",
    url: "https://aclanthology.org/E06-1032/",
  },
];

export default function CompareChatGptPage() {
  const breadcrumb = breadcrumbJsonLd([
    { name: "Home", path: "/" },
    { name: "Compare", path: "/compare/chatgpt-prompt" },
    { name: "A single ChatGPT prompt" },
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
            <BreadcrumbNav items={[{ name: "Home", path: "/" }, { name: "Compare", path: "/compare/chatgpt-prompt" }, { name: "A single ChatGPT prompt" }]} />
            <h1 className="mt-3 font-serif text-3xl text-ink dark:text-ink-dark sm:text-4xl">
              Castia vs. a single ChatGPT prompt.
            </h1>
            <p className="mt-4 max-w-prose text-[15px] leading-relaxed text-ink/78 dark:text-ink-dark/78">
              "Just ask an LLM to translate it creatively" is a genuinely
              reasonable instinct - a modern chat model can absolutely
              produce a creative rewrite of a line. The question is what
              you're left with once it does.
            </p>
          </div>
          <CompareDiagram competitorName="One ChatGPT prompt" competitorStep="One generation, no check" />
        </div>

        <section className="mt-12">
          <h2 className="font-serif text-xl text-ink dark:text-ink-dark">
            What one prompt actually gives you
          </h2>
          <p className="mt-3 max-w-prose text-[14px] leading-relaxed text-ink/72 dark:text-ink-dark/72">
            One prompt, one response: a single rewrite, produced in one
            pass, with nothing else to compare it to. If it's good, you
            have no way to tell how good relative to the alternatives the
            model didn't show you. If it's drifted from what the line
            actually says, there's nothing in that single response that
            would tell you - the model wasn't asked to check its own work
            against a literal reading, only to produce a creative one.
          </p>
          <p className="mt-3 max-w-prose text-[14px] leading-relaxed text-ink/72 dark:text-ink-dark/72">
            This isn't a knock on the model's capability. It's a gap in the
            process: a single generation step has no built-in mechanism for
            catching its own semantic drift, and research on automated
            translation evaluation (Callison-Burch et al., 2006) shows that
            even a fluent, confident-sounding output can diverge from
            source meaning in ways that are easy to miss without a separate
            check.
          </p>
        </section>

        <section className="mt-12">
          <h2 className="font-serif text-xl text-ink dark:text-ink-dark">
            What a verified pipeline adds
          </h2>
          <p className="mt-3 max-w-prose text-[14px] leading-relaxed text-ink/72 dark:text-ink-dark/72">
            Castia runs the same underlying kind of model through three
            distinct roles instead of one prompt: a Translator produces a
            literal anchor first, a Creative Adapter produces five
            differently-angled rewrites, and a Judge scores every rewrite
            against that anchor and against each other, picking a winner
            and writing down the specific reason it departs from a literal
            reading. If none of the five earns a genuine improvement, the
            literal anchor ships instead of a manufactured difference.
          </p>
          <p className="mt-3 max-w-prose text-[14px] leading-relaxed text-ink/72 dark:text-ink-dark/72">
            Using a model to score another model's output against a rubric
            - "LLM-as-a-judge" - is an actively researched evaluation
            approach, not something invented for this comparison: NeurIPS
            2023 research (Zheng et al.) found strong LLM judges can match
            human preference on open-ended tasks over 80% of the time,
            while also documenting real biases (favoring longer answers,
            position in a list, a model favoring its own outputs) that a
            judge stage has to be designed around rather than ignore. The
            point isn't that a Judge stage is infallible - it's that a
            single prompt has no equivalent check at all.
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
                  <th className="p-4 font-medium text-ink/68 dark:text-ink-dark/68"> </th>
                  <th className="p-4 font-medium text-ink dark:text-ink-dark">One ChatGPT prompt</th>
                  <th className="p-4 font-medium text-ink dark:text-ink-dark">Castia</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-black/[0.10] dark:divide-white/[0.11]">
                {[
                  ["Drafts produced", "One", "Six (one literal anchor + five creative rewrites)"],
                  ["Checked against a literal reading", "No", "Yes - every rewrite is scored against the anchor"],
                  ["Stated reason for each change", "No", "Yes"],
                  ["Falls back to literal if nothing earns its keep", "No mechanism for this", "Yes"],
                  ["Repeatable / cached", "Re-run from scratch each time", "Same input returns the same verified result"],
                ].map(([label, gpt, castia]) => (
                  <tr key={label}>
                    <td className="p-4 text-ink/68 dark:text-ink-dark/68">{label}</td>
                    <td className="p-4 text-ink/78 dark:text-ink-dark/78">{gpt}</td>
                    <td className="p-4 text-ink/78 dark:text-ink-dark/78">{castia}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* The "same line, run through both" side-by-side used to render
            here - a dashed "Screenshot pending" box, since no real
            capture ever existed for the six images this page and its
            siblings pointed at (running an actual line through
            ChatGPT/DeepL/Google Translate and Castia to capture it needs
            live API credentials this project doesn't have). Shipping a
            visibly broken "pending" placeholder to real visitors is worse
            than not having the section - removed until real screenshots
            exist to fill it, same discipline MockWindow.tsx's own doc
            comment states for why nothing here gets faked instead. The
            component that rendered it (ScreenshotSlot.tsx) had no other
            callers once this and its two sibling pages dropped it, so it
            was deleted rather than left as dead code. */}
        {/* dark:border-white/[0.12] - this card's fixed dark background
            (#181310) is the exact same hex as the page's own dark-mode
            background, confirmed via computed styles - with no border it
            was completely invisible as a card in dark mode specifically. */}
        <div className="mt-14 rounded-2xl bg-[#181310] p-8 text-center dark:border dark:border-white/[0.12] sm:p-10">
          <p className="font-serif text-xl text-white sm:text-2xl">
            See the whole pipeline on one line.
          </p>
          <p className="mt-2 max-w-md mx-auto text-[13px] leading-relaxed text-white/68">
            The literal anchor, all five rewrites, and the Judge's reasoning
            - not just the one line a single prompt would have given you.
          </p>
          <Link
            href="/music"
            className="mt-6 inline-block rounded-full bg-white px-6 py-2.5 text-[13px] font-medium text-black transition active:scale-[0.97]"
          >
            Try it on a lyric
          </Link>
        </div>

        <p className="mt-8 max-w-prose text-[13px] leading-relaxed text-ink/75 dark:text-ink-dark/75">
          Also see{" "}
          <Link href="/compare/google-translate" className="underline decoration-ink/20 underline-offset-4">
            Castia vs. Google Translate
          </Link>{" "}
          and{" "}
          <Link href="/compare/deepl" className="underline decoration-ink/20 underline-offset-4">
            Castia vs. DeepL
          </Link>
          .
        </p>

        <SourceList sources={SOURCES} />

        <Footer />
      </div>
    </main>
  );
}

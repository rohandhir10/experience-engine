import { SiteHeader } from "@/components/SiteHeader";
import { Footer } from "@/components/Footer";
import { JsonLd } from "@/components/JsonLd";
import { BreadcrumbNav } from "@/components/BreadcrumbNav";
import { SourceList } from "@/components/SourceList";
import { ComicsPipelineDiagram } from "@/components/ComicsPipelineDiagram";
import Link from "next/link";
import { contentByPath } from "@/lib/content";
import { breadcrumbJsonLd, articleJsonLd, howToJsonLd } from "@/lib/schema";

const entry = contentByPath("/how-it-works")!;

export const metadata = {
  title: entry.title,
  description: entry.description,
  alternates: { canonical: entry.path },
};

const SOURCES = [
  {
    name: "Wu et al., \"Google's Neural Machine Translation System\" (2016), Google Research / arXiv",
    url: "https://arxiv.org/abs/1609.08144",
    note: "what a single-pass neural MT system is architecturally optimized to do",
  },
  {
    name: "Callison-Burch, Osborne & Koehn, \"Re-evaluating the Role of BLEU in Machine Translation Research\" (EACL 2006)",
    url: "https://aclanthology.org/E06-1032/",
    note: "why an automated closeness score doesn't reliably track human-judged quality - the reason a Judge stage exists instead of a metric",
  }
];

// Original artwork, not a screenshot - visualizes the specific mechanism
// Step 2/3 below describe in prose: five differently-angled rewrites
// scored against the literal anchor, with one picked and the rest left
// behind. The remaining ComicsPipelineDiagram shows the stage flow;
// this is the selection itself.
function CandidateDiagram() {
  const others = [1, 2, 3, 4];
  return (
    <div className="rounded-2xl border border-black/[0.12] bg-paper p-6 dark:border-white/[0.12] dark:bg-paper-dark sm:p-7">
      <p className="text-[10px] font-medium uppercase tracking-[0.1em] text-ink/68 dark:text-ink-dark/68">
        Five rewrites, scored against the anchor
      </p>
      <div className="mt-4 space-y-2">
        <div className="flex items-center gap-3 rounded-lg border border-accent/40 bg-accent/[0.06] px-3 py-2">
          <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-accent text-[10px] font-medium text-paper">
            ✓
          </span>
          <p className="font-serif text-[13px] leading-snug text-ink dark:text-ink-dark">
            &ldquo;You came back. I knew you would.&rdquo;
          </p>
        </div>
        {others.map((i) => (
          <div key={i} className="flex items-center gap-3 rounded-lg px-3 py-2 opacity-40">
            <span className="h-5 w-5 shrink-0 rounded-full border border-ink/20 dark:border-ink-dark/20" />
            <p className="font-serif text-[13px] leading-snug text-ink/72 dark:text-ink-dark/72">
              Rewrite {i}
            </p>
          </div>
        ))}
      </div>
      <p className="mt-4 border-t border-black/[0.10] pt-4 text-[12.5px] italic leading-relaxed text-ink/68 dark:border-white/[0.10] dark:text-ink-dark/68">
        &ldquo;Kept the character&rsquo;s guarded tone while making the line sound natural in this scene.&rdquo;
      </p>
    </div>
  );
}

export default function HowItWorksPage() {
  const breadcrumb = breadcrumbJsonLd([
    { name: "Home", path: "/" },
    { name: "How it works" },
  ]);
  const article = articleJsonLd({
    path: entry.path,
    headline: entry.title,
    description: entry.description,
    publishedDate: entry.publishedDate,
    updatedDate: entry.updatedDate,
    citations: SOURCES,
  });
  const howTo = howToJsonLd({
    path: entry.path,
    name: "How CASTIA adapts comic dialogue",
    description:
      "The review process for comic and webtoon dialogue, from extracted text to an adaptation with an explicit rationale.",
    steps: [
      {
        name: "Translator",
        text: "Produce one literal, anchor translation of the source line - not shown as the final output, but the fixed reference every later rewrite is checked against.",
      },
      {
        name: "Creative Adapter",
        text: "Produce five differently-angled creative rewrites of the same line, each taking a distinct liberty with phrasing, idiom, or rhythm.",
      },
      {
        name: "Judge",
        text: "Score each of the five rewrites against the literal anchor, pick a winner, and write down the specific reason it departs from a literal reading. If none of the five earns a genuine improvement, the literal anchor ships instead.",
      },
    ],
  });

  return (
    <main className="min-h-screen px-6 pb-28 pt-8 sm:px-10">
      <JsonLd data={breadcrumb} />
      <JsonLd data={article} />
      <JsonLd data={howTo} />
      <div className="mx-auto max-w-3xl">
        <SiteHeader />

        <div className="mt-10 grid grid-cols-1 gap-10 lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
          <div>
            <BreadcrumbNav items={[{ name: "Home", path: "/" }, { name: "How it works" }]} />
            <h1 className="mt-3 font-serif text-3xl leading-[1.15] text-ink dark:text-ink-dark sm:text-4xl">
              Five rewrites compete for every line.
              <br />
              One wins, and it has to say why.
            </h1>
            <p className="mt-4 max-w-prose text-[15px] leading-relaxed text-ink/78 dark:text-ink-dark/78">
              Every dialogue line goes through a structured review process. Each adaptation is checked against the source and comes with a plain-language reason for creative changes.
            </p>
          </div>
          <CandidateDiagram />
        </div>

        <div className="mt-12 space-y-6">
          <Step
            n="1"
            title="Translator"
            body="Produces one literal, anchor translation of the source line. This isn't shown as the final output — it's the floor everything else is checked against, so a later rewrite can be judged against what the line actually says, not just what it might mean."
          />
          <Step
            n="2"
            title="Creative Adapter"
            body="Produces five differently-angled creative rewrites of the same line, each taking a different liberty with phrasing, idiom, or rhythm — never five copies of the same idea."
          />
          <Step
            n="3"
            title="Judge"
            body="Scores each of the five rewrites against the Translator's literal anchor and against each other, picks a winner, and writes down the specific, real reason it departs from a literal translation. If none of the five earns a genuine improvement, the literal anchor ships instead of a manufactured difference."
          />
        </div>

        <section className="mt-14 border-t border-black/[0.10] pt-10 dark:border-white/[0.11]">
          <h2 className="font-serif text-xl text-ink dark:text-ink-dark">
            Why five rewrites and a Judge, not one pass
          </h2>
          <p className="mt-3 max-w-prose text-[14px] leading-relaxed text-ink/72 dark:text-ink-dark/72">
            A fluent translation can still miss what makes a line work in a comic: the character speaking, the relationship between speakers, the surrounding artwork, and the moment in the story. Comparing alternatives against the source helps editors see those trade-offs instead of accepting the first plausible rewrite.
          </p>
          <p className="mt-3 max-w-prose text-[14px] leading-relaxed text-ink/72 dark:text-ink-dark/72">
            It's also why the Judge is a scoring model reading against a
            literal anchor, not an automated metric like BLEU. Callison-Burch
            et al.'s 2006 analysis of BLEU — the standard automated
            translation-quality score — found that a higher BLEU score
            doesn't reliably track a better human-judged translation,
            because BLEU rewards closeness to one reference wording, not
            whether a differently-worded line captures the same feeling
            better. Scoring against the literal anchor's actual meaning,
            the way the Judge does, sidesteps that specific blind spot.
          </p>
          <p className="mt-3 max-w-prose text-[14px] leading-relaxed text-ink/72 dark:text-ink-dark/72">
            Before a rewrite ever reaches the Judge, it's also checked for a
            specific set of failure patterns an automated pass can catch
            reliably: dialogue being flattened into an unnatural block of prose, or a rewrite so close to the source that it offers no meaningful improvement. A rewrite that trips one of these
            checks is sent back for a fresh attempt before it's ever put in
            front of the Judge, rather than being scored as-is.
          </p>
        </section>

        <div className="mt-14 rounded-2xl bg-[#141a2b] p-8 sm:p-10">
          <p className="text-[12px] uppercase tracking-[0.15em] text-white/62">
            Webtoons &amp; comics
          </p>
          <h2 className="mt-3 max-w-lg font-serif text-[1.5rem] leading-[1.25] text-white sm:text-[1.7rem]">
            OCR, a cast profile, then the identical Writers' Room.
          </h2>
          <p className="mt-3 max-w-xl text-[13px] leading-relaxed text-white/62">
            A chapter's panels go through Google Cloud Vision OCR, which
            detects each speech bubble's text and the order it's meant to
            be read in. Before any line is translated, a separate pass
            reads the whole chapter and builds its Chapter DNA — a profile
            of who's speaking, how each character speaks, and the tone of
            the scene — so a character's established voice carries into the
            per-bubble prompt for every one of their lines, not just the
            first. From there, every line runs through the same
            structured review process — with a clear source reference and a reason for each creative change.
          </p>
          <p className="mt-3 max-w-xl text-[13px] leading-relaxed text-white/62">
            An optional redraw pass can erase the original lettering,
            inpaint the artwork underneath it, and typeset the adapted line
            back into the bubble — with overlapping speech bubbles merged
            into a single region before typesetting so text doesn't
            collide, a font picked per region or set as a page default from
            a bundled set of open-license comic lettering fonts, and a
            bounded retry if the inpainting service call fails rather than
            leaving a panel half-processed.
          </p>
          <div className="mt-8">
            <ComicsPipelineDiagram />
          </div>
        </div>

        <p className="mt-12 max-w-prose text-[14px] leading-relaxed text-ink/68 dark:text-ink-dark/68">
          Try it on a real result first —{" "}
          <Link href="/s/demo" className="underline decoration-ink/20 underline-offset-4">
            see the worked example
          </Link>{" "}
          or read the{" "}
          <Link href="/faq" className="underline decoration-ink/20 underline-offset-4">
            FAQ
          </Link>
          .
        </p>

        <SourceList sources={SOURCES} />

        <Footer />
      </div>
    </main>
  );
}

function Step({ n, title, body }: { n: string; title: string; body: string }) {
  return (
    <div className="flex gap-5">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-black/10 font-serif text-[13px] text-ink/68 dark:border-white/10 dark:text-ink-dark/68">
        {n}
      </div>
      <div>
        <h3 className="font-serif text-lg text-ink dark:text-ink-dark">{title}</h3>
        <p className="mt-1.5 max-w-prose text-[14px] leading-relaxed text-ink/72 dark:text-ink-dark/72">
          {body}
        </p>
      </div>
    </div>
  );
}

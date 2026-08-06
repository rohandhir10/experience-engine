import { SiteHeader } from "@/components/SiteHeader";
import { Footer } from "@/components/Footer";
import { JsonLd } from "@/components/JsonLd";
import { BreadcrumbNav } from "@/components/BreadcrumbNav";
import { SourceList } from "@/components/SourceList";
import { PipelineDiagramDark } from "@/components/PipelineDiagramDark";
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

// Same three citations the /compare pages use - legitimate to reuse here
// too, since this page makes the same underlying claim (why one fluent
// pass isn't enough for a lyric or a character's voice) in more depth,
// not a marketing sentence being pasted twice.
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
  },
  {
    name: "Low, P., \"Singable Translations of Songs\" (2003), Perspectives: Studies in Translatology",
    url: "https://www.tandfonline.com/doi/abs/10.1080/0907676X.2003.9961466",
    note: "the \"Pentathlon Principle\" - five demands a singable lyric has to balance at once",
  },
];

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
    name: "How Castia adapts a line of dialogue or lyric",
    description:
      "The three-stage pipeline every line runs through before it ships, whether the source is a song lyric or a comic panel's dialogue.",
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

        <div className="mt-10">
          <BreadcrumbNav items={[{ name: "Home", path: "/" }, { name: "How it works" }]} />
          <h1 className="mt-3 font-serif text-3xl text-ink dark:text-ink-dark sm:text-4xl">
            A real Writers' Room, not one prompt.
          </h1>
          <p className="mt-4 max-w-prose text-[15px] leading-relaxed text-ink/55 dark:text-ink-dark/55">
            Castia doesn't ask a single model to translate a line and call
            it done. Every line — whether it's a song lyric or a comic
            panel's dialogue — goes through the same three-stage pipeline,
            and every departure from a literal translation ships with a
            plain-language reason instead of a silent rewrite.
          </p>
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

        <section className="mt-14 border-t border-black/[0.06] pt-10 dark:border-white/[0.07]">
          <h2 className="font-serif text-xl text-ink dark:text-ink-dark">
            Why five rewrites and a Judge, not one pass
          </h2>
          <p className="mt-3 max-w-prose text-[14px] leading-relaxed text-ink/60 dark:text-ink-dark/60">
            A standard neural machine translation system — the kind behind
            Google Translate and DeepL — is architecturally built to decode
            a single, most-probable target-language sentence and return it.
            That's the right design for sentence-level accuracy, and it's
            not the design a lyric needs: translation researcher Peter
            Low's "Pentathlon Principle" names five demands a singable lyric
            translation has to balance at once — singability, sense,
            naturalness, rhythm, and rhyme — and argues that optimizing for
            literal accuracy alone actively produces worse lyric
            translations. A single-pass system has no mechanism for making
            that tradeoff on purpose.
          </p>
          <p className="mt-3 max-w-prose text-[14px] leading-relaxed text-ink/60 dark:text-ink-dark/60">
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
          <p className="mt-3 max-w-prose text-[14px] leading-relaxed text-ink/60 dark:text-ink-dark/60">
            Before a rewrite ever reaches the Judge, it's also checked for a
            specific set of failure patterns an automated pass can catch
            reliably: short lyric lines collapsing into one run-on prose
            paragraph, or a rewrite so close to the anchor that it isn't
            really a rewrite at all, just claiming credit for a stylistic
            change that didn't happen. A rewrite that trips one of these
            checks is sent back for a fresh attempt before it's ever put in
            front of the Judge, rather than being scored as-is.
          </p>
        </section>

        <div className="mt-14 rounded-2xl bg-[#181310] p-8 sm:p-10">
          <p className="text-[12px] uppercase tracking-[0.15em] text-white/25">Music</p>
          <h2 className="mt-3 max-w-lg font-serif text-[1.5rem] leading-[1.25] text-white sm:text-[1.7rem]">
            Source lyrics in, verified output out.
          </h2>
          <p className="mt-3 max-w-xl text-[13px] leading-relaxed text-white/40">
            Six languages, either direction — English, Hindi, Japanese,
            Korean, Spanish, and Urdu — each with its own language profile
            so idiom and rhythm checks apply the rules that actually govern
            that language, not one generic ruleset stretched across all six.
            Results are cached by the content itself, so re-submitting the
            same lyric doesn't re-run the pipeline from scratch.
          </p>
          <div className="mt-8">
            <PipelineDiagramDark />
          </div>
        </div>

        <div className="mt-8 rounded-2xl bg-[#141a2b] p-8 sm:p-10">
          <p className="text-[12px] uppercase tracking-[0.15em] text-white/25">
            Webtoons &amp; comics (Beta)
          </p>
          <h2 className="mt-3 max-w-lg font-serif text-[1.5rem] leading-[1.25] text-white sm:text-[1.7rem]">
            OCR, a cast profile, then the identical Writers' Room.
          </h2>
          <p className="mt-3 max-w-xl text-[13px] leading-relaxed text-white/40">
            A chapter's panels go through Google Cloud Vision OCR, which
            detects each speech bubble's text and the order it's meant to
            be read in. Before any line is translated, a separate pass
            reads the whole chapter and builds its Chapter DNA — a profile
            of who's speaking, how each character speaks, and the tone of
            the scene — so a character's established voice carries into the
            per-bubble prompt for every one of their lines, not just the
            first. From there, every line runs through the same
            Translator → Creative Adapter → Judge pipeline the music side
            uses — not a separate, lesser engine.
          </p>
          <p className="mt-3 max-w-xl text-[13px] leading-relaxed text-white/40">
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

        <p className="mt-12 max-w-prose text-[14px] leading-relaxed text-ink/50 dark:text-ink-dark/50">
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
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-black/10 font-serif text-[13px] text-ink/50 dark:border-white/10 dark:text-ink-dark/50">
        {n}
      </div>
      <div>
        <h3 className="font-serif text-lg text-ink dark:text-ink-dark">{title}</h3>
        <p className="mt-1.5 max-w-prose text-[14px] leading-relaxed text-ink/60 dark:text-ink-dark/60">
          {body}
        </p>
      </div>
    </div>
  );
}

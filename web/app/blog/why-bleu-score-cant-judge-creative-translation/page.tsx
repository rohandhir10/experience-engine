import Link from "next/link";
import { BlogPostShell } from "@/components/BlogPostShell";
import { contentByPath } from "@/lib/content";

const entry = contentByPath("/blog/why-bleu-score-cant-judge-creative-translation")!;

export const metadata = {
  title: entry.title,
  description: entry.description,
  alternates: { canonical: entry.path },
};

const SOURCES = [
  {
    name: "Callison-Burch, Osborne & Koehn, \"Re-evaluating the Role of BLEU in Machine Translation Research\" (EACL 2006)",
    url: "https://aclanthology.org/E06-1032/",
    note: "an improved BLEU score is neither necessary nor sufficient for an actual improvement in translation quality",
  },
  {
    name: "Zheng et al., \"Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena\" (NeurIPS 2023)",
    url: "https://arxiv.org/abs/2306.05685",
    note: "strong LLM judges can match human preference well, with documented biases",
  },
];

export default function Post() {
  return (
    <BlogPostShell
      entry={entry}
      citations={SOURCES}
      cta={{
        heading: "See a Judge's actual reasoning.",
        body: "Every adapted line ships with the specific reason it departs from a literal translation.",
        href: "/how-it-works",
        label: "See how it works",
      }}
    >
      <p className="max-w-prose text-[14px] leading-relaxed text-ink/65 dark:text-ink-dark/65">
        BLEU has been the default automated metric for judging machine
        translation quality for two decades - it's fast, cheap, and gives
        you a single number. It was also never built to tell you whether a
        creative rewrite is good, and the research saying so predates most
        of today's LLM-based translation tools by more than fifteen years.
      </p>

      <h2 className="font-serif text-xl text-ink dark:text-ink-dark">
        What BLEU actually measures
      </h2>
      <p className="max-w-prose text-[14px] leading-relaxed text-ink/65 dark:text-ink-dark/65">
        BLEU scores a candidate translation by how many of its word
        sequences overlap with one or more human reference translations.
        Callison-Burch, Osborne, and Koehn's 2006 EACL paper,{" "}
        <em>Re-evaluating the Role of BLEU in Machine Translation Research</em>,
        is the paper most often cited for what that leaves out: it argues,
        with direct evidence, that an improved BLEU score is "neither
        necessary nor sufficient" for an actual improvement in translation
        quality as judged by a human. A translation that rewords a
        sentence correctly, but differently from the reference, can score
        worse than a translation that's closer to the reference wording
        but reads more awkwardly.
      </p>
      <p className="max-w-prose text-[14px] leading-relaxed text-ink/65 dark:text-ink-dark/65">
        That's a fundamental mismatch for creative adaptation specifically:
        the entire point of a creative rewrite is to depart from the most
        literal wording on purpose. A metric that rewards closeness to one
        reference string will always penalize the thing a good adaptation
        is trying to do.
      </p>

      <h2 className="font-serif text-xl text-ink dark:text-ink-dark">
        Using a model to judge a model
      </h2>
      <p className="max-w-prose text-[14px] leading-relaxed text-ink/65 dark:text-ink-dark/65">
        One alternative that's gotten real research attention is
        "LLM-as-a-judge" - having a language model score or rank other
        outputs against a rubric, instead of a fixed formula like BLEU.
        Zheng et al.'s 2023 NeurIPS paper,{" "}
        <em>Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena</em>,
        found that a strong LLM judge (GPT-4, in their study) can match
        both controlled and crowdsourced human preference well - the paper
        reports over 80% agreement, comparable to the agreement level
        between two human raters.
      </p>
      <p className="max-w-prose text-[14px] leading-relaxed text-ink/65 dark:text-ink-dark/65">
        The same paper is just as clear about the catch: LLM judges carry
        real, documented biases - favoring longer answers regardless of
        quality, favoring whichever position an answer appears in, and
        favoring a model's own outputs over a competitor's. A judge stage
        that ignores those failure modes isn't actually solving BLEU's
        problem, just moving it somewhere less visible.
      </p>

      <h2 className="font-serif text-xl text-ink dark:text-ink-dark">
        Why a Judge needs an anchor
      </h2>
      <p className="max-w-prose text-[14px] leading-relaxed text-ink/65 dark:text-ink-dark/65">
        Castia's Judge stage is built around that specific caveat: it
        doesn't rank rewrites purely on open-ended preference, which is
        where position and verbosity bias creep in unchecked - it scores
        each rewrite against a literal anchor translation produced by a
        separate Translator stage first. That anchor is the fixed
        reference point BLEU never had a creative-translation-appropriate
        version of, and it's what lets the Judge state a specific reason a
        rewrite earns its departure from a literal reading, rather than
        just a preference score. See the full pipeline on{" "}
        <Link href="/how-it-works" className="underline decoration-ink/20 underline-offset-4">
          how it works
        </Link>
        .
      </p>
    </BlogPostShell>
  );
}

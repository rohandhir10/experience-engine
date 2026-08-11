import Link from "next/link";
import { BlogPostShell } from "@/components/BlogPostShell";
import { contentByPath } from "@/lib/content";

const entry = contentByPath("/blog/what-transcreation-means")!;

export const metadata = {
  title: entry.title,
  description: entry.description,
  alternates: { canonical: entry.path },
};

const SOURCES = [
  {
    name: "GALA (Globalization and Localization Association), \"Transcreation - What Is It?\"",
    url: "https://www.gala-global.org/blog/transcreation-%E2%80%93-what-it",
    note: "industry-association definition distinguishing transcreation from localization",
  },
  {
    name: "American Translators Association, \"Transcreation: Translating and Recreating\"",
    url: "https://www.atanet.org/client-assistance/transcreation-translating-and-recreating/",
    note: "client-facing definition of transcreation preserving message, style, and emotional impact",
  },
];

export default function Post() {
  return (
    <BlogPostShell
      entry={entry}
      citations={SOURCES}
      cta={{
        heading: "See transcreation applied, not just defined.",
        body: "A literal anchor, five creative rewrites, and a stated reason for the one that wins.",
        href: "/how-it-works",
        label: "See how it works",
      }}
    >
      <p className="max-w-prose text-[14px] leading-relaxed text-ink/75 dark:text-ink-dark/75">
        "Transcreation" gets used loosely, but it has an actual origin and
        an actual definition in the localization industry - and it names
        precisely the gap between translating words and adapting a
        feeling.
      </p>

      <h2 className="font-serif text-xl text-ink dark:text-ink-dark">
        Where the term comes from
      </h2>
      <p className="max-w-prose text-[14px] leading-relaxed text-ink/75 dark:text-ink-dark/75">
        GALA (the Globalization and Localization Association, one of the
        industry's main trade bodies) describes transcreation as going a
        step further than localization: where localization adapts
        existing content to a target culture's expectations, transcreation
        effectively starts over, recreating a piece of content so its
        intent, style, tone, and emotional impact survive the trip into
        another language - even when the actual words don't. The American
        Translators Association's client-facing description makes the same
        point from a different angle: transcreation aims to keep a text's
        message, style, imagery, and emotional effect equivalent to the
        original, treating the words themselves as the most negotiable
        part of that equation, not the least.
      </p>

      <h2 className="font-serif text-xl text-ink dark:text-ink-dark">
        Not just marketing copy
      </h2>
      <p className="max-w-prose text-[14px] leading-relaxed text-ink/75 dark:text-ink-dark/75">
        The term is most associated with advertising - a slogan built
        around a pun or a cultural reference has to be rebuilt from
        scratch in another language, not translated, or it simply stops
        working. But the underlying problem isn't specific to marketing:
        anywhere a piece of content's effect depends on rhythm, wordplay,
        connotation, or a shared cultural reference, a literal translation
        risks preserving the words while losing the actual point. A song
        lyric built around a rhyme, or a character's line built around a
        specific idiom, is the same problem in a different genre.
      </p>

      <h2 className="font-serif text-xl text-ink dark:text-ink-dark">
        Making the tradeoff on purpose
      </h2>
      <p className="max-w-prose text-[14px] leading-relaxed text-ink/75 dark:text-ink-dark/75">
        The risk in transcreation is the same risk in any adaptation that
        departs from the literal: without something to check it against,
        a rewrite can drift from what the source actually meant, not just
        how it said it. Castia's Writers' Room is built around keeping
        that check in place - a literal anchor translation first, several
        creative rewrites second, and a Judge stage that scores each
        rewrite against the anchor and states the specific reason it earns
        its departure, rather than assuming a creative rewrite is
        automatically faithful just because it reads well. See the
        mechanics on{" "}
        <Link href="/how-it-works" className="underline decoration-ink/20 underline-offset-4">
          how it works
        </Link>
        , or look up related terms in the{" "}
        <Link href="/glossary" className="underline decoration-ink/20 underline-offset-4">
          glossary
        </Link>
        .
      </p>
    </BlogPostShell>
  );
}

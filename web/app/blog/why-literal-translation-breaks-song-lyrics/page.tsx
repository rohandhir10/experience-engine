import Link from "next/link";
import { BlogPostShell } from "@/components/BlogPostShell";
import { contentByPath } from "@/lib/content";

const entry = contentByPath("/blog/why-literal-translation-breaks-song-lyrics")!;

export const metadata = {
  title: entry.title,
  description: entry.description,
  alternates: { canonical: entry.path },
};

const SOURCES = [
  {
    name: "Low, P., \"Singable Translations of Songs\" (2003), Perspectives: Studies in Translatology, 11(2)",
    url: "https://www.tandfonline.com/doi/abs/10.1080/0907676X.2003.9961466",
    note: "the \"Pentathlon Principle\" for lyric translation",
  },
  {
    name: "Greene, Bodrumlu & Knight, \"'Poetic' Statistical Machine Translation: Rhyme and Meter\" (EMNLP 2010)",
    url: "https://aclanthology.org/D10-1016.pdf",
    note: "imposing rhyme/meter constraints on MT measurably trades off against literal accuracy",
  },
];

export default function Post() {
  return (
    <BlogPostShell
      entry={entry}
      citations={SOURCES}
      cta={{
        heading: "See it applied to a real lyric.",
        body: "Paste a verse and get the literal anchor, five rewrites, and the reasoning behind the winner.",
        href: "/music",
        label: "Try it on a lyric",
      }}
    >
      <p className="max-w-prose text-[14px] leading-relaxed text-ink/65 dark:text-ink-dark/65">
        Ask a machine translation engine to translate a song lyric and
        you'll get something that's often technically accurate and almost
        never singable. That's not a bug in the engine - it's a mismatch
        between what literal translation optimizes for and what a lyric
        actually needs to do.
      </p>

      <h2 className="font-serif text-xl text-ink dark:text-ink-dark">
        Five demands, not one
      </h2>
      <p className="max-w-prose text-[14px] leading-relaxed text-ink/65 dark:text-ink-dark/65">
        Translation researcher Peter Low's 2003 paper in{" "}
        <em>Perspectives: Studies in Translatology</em> names this problem
        directly with what he calls the "Pentathlon Principle": a singable
        lyric translation has to balance five competing demands at
        once - singability, sense, naturalness, rhythm, and rhyme - the
        way a pentathlete has to be competitive across five different
        events rather than dominant at just one. Low's argument is that
        treating any single demand (including literal semantic accuracy)
        as sacrosanct actively produces a worse lyric translation, because
        it forces the other four to break.
      </p>
      <p className="max-w-prose text-[14px] leading-relaxed text-ink/65 dark:text-ink-dark/65">
        A word-for-word rendering of a line can satisfy "sense" almost
        perfectly and still fail every other demand - it won't scan
        against the melody, it won't rhyme where the original did, and it
        can read as stilted rather than natural in the target language.
      </p>

      <h2 className="font-serif text-xl text-ink dark:text-ink-dark">
        The tradeoff is real, and measurable
      </h2>
      <p className="max-w-prose text-[14px] leading-relaxed text-ink/65 dark:text-ink-dark/65">
        This isn't just translator intuition. A 2010 EMNLP paper by
        Greene, Bodrumlu, and Knight built a statistical MT system that
        explicitly constrains its output to fit rhyme and meter, and found
        that doing so measurably trades off against standard MT accuracy
        scores - the more a translation is shaped to fit poetic form, the
        further it tends to drift from a literal rendering, by
        construction. The tradeoff Low describes qualitatively shows up as
        an actual, quantified cost when you try to optimize for both at
        once.
      </p>

      <h2 className="font-serif text-xl text-ink dark:text-ink-dark">
        What this means for adapting a lyric
      </h2>
      <p className="max-w-prose text-[14px] leading-relaxed text-ink/65 dark:text-ink-dark/65">
        If a good lyric translation genuinely requires departing from a
        literal reading, the departure has to be made on purpose, with
        something to check it against - not left to whatever a single
        translation pass happens to produce. That's the reasoning behind
        Castia's three-stage approach: a literal anchor translation first
        (so there's a real floor to check against), several
        differently-angled creative rewrites, and a Judge stage that picks a winner
        and states the specific reason it earns its departure from the
        anchor. See the mechanics on{" "}
        <Link href="/how-it-works" className="underline decoration-ink/20 underline-offset-4">
          how it works
        </Link>
        .
      </p>
    </BlogPostShell>
  );
}

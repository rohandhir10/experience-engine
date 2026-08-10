import { SiteHeader } from "@/components/SiteHeader";
import { Footer } from "@/components/Footer";
import { JsonLd } from "@/components/JsonLd";
import { BreadcrumbNav } from "@/components/BreadcrumbNav";
import Link from "next/link";
import { contentByPath } from "@/lib/content";
import { breadcrumbJsonLd, articleJsonLd } from "@/lib/schema";

const entry = contentByPath("/lyrics-translation")!;

export const metadata = {
  title: entry.title,
  description: entry.description,
  alternates: { canonical: entry.path },
};

const LANGUAGES = ["English", "Japanese", "Korean", "Spanish", "Urdu", "Hindi"];

// Original artwork, not a screenshot - grounded in the real Judge
// behavior described in how-it-works: a literal anchor line, an adapted
// line, and the Judge's stated reason for the departure. Deliberately a
// generic English couplet rather than a real lyric in one of the six
// supported languages, so nothing here claims translation accuracy it
// hasn't earned.
function LyricLineDiagram() {
  return (
    <div className="relative overflow-hidden rounded-2xl border border-black/[0.08] bg-paper p-6 dark:border-white/[0.08] dark:bg-paper-dark sm:p-7">
      <p className="text-[10px] font-medium uppercase tracking-[0.1em] text-ink/35 dark:text-ink-dark/35">
        Literal
      </p>
      <p className="mt-1.5 font-serif text-[15px] leading-snug text-ink/50 line-through decoration-ink/20 dark:text-ink-dark/50 dark:decoration-ink-dark/20">
        The night doesn't end, it only grows quiet.
      </p>

      <div className="relative my-5 h-8">
        <svg className="absolute left-3 h-full w-[calc(100%-24px)] text-accent/50" viewBox="0 0 200 32" preserveAspectRatio="none" aria-hidden="true">
          <path d="M 4 4 C 60 4, 60 28, 196 28" fill="none" stroke="currentColor" strokeWidth="1.5" strokeDasharray="3 5" />
        </svg>
        <span className="absolute right-0 top-0 rounded-full bg-accent px-2 py-0.5 text-[10px] font-medium text-paper">
          Judge
        </span>
      </div>

      <p className="text-[10px] font-medium uppercase tracking-[0.1em] text-ink/35 dark:text-ink-dark/35">
        Adapted
      </p>
      <p className="mt-1.5 font-serif text-[16px] leading-snug text-ink dark:text-ink-dark">
        The night won't end - it just goes quiet.
      </p>

      <p className="mt-5 border-t border-black/[0.06] pt-4 text-[12.5px] italic leading-relaxed text-ink/50 dark:border-white/[0.06] dark:text-ink-dark/50">
        &ldquo;Kept the near-rhyme on end / quiet, dropped the literal
        &lsquo;grows&rsquo; to make it singable against the melody.&rdquo;
      </p>
    </div>
  );
}

export default function LyricsTranslationPage() {
  const breadcrumb = breadcrumbJsonLd([
    { name: "Home", path: "/" },
    { name: "Song lyric translation" },
  ]);
  // articleJsonLd, not webPageJsonLd - matches its sibling
  // manga-webtoon-translation, and is the more accurate type for this
  // page: real published/updated dates and a real author (see
  // lib/seo.ts's FOUNDER_NAME), the same shape Google's Article rich
  // result expects, which a generic WebPage never was.
  const article = articleJsonLd({
    path: entry.path,
    headline: entry.title,
    description: entry.description,
    publishedDate: entry.publishedDate,
    updatedDate: entry.updatedDate,
  });

  return (
    <main className="min-h-screen px-6 pb-28 pt-8 sm:px-10">
      <JsonLd data={breadcrumb} />
      <JsonLd data={article} />
      <div className="mx-auto max-w-3xl">
        <SiteHeader />

        <div className="mt-10 grid grid-cols-1 gap-10 lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
          <div>
            <BreadcrumbNav items={[{ name: "Home", path: "/" }, { name: "Song lyric translation" }]} />
            <h1 className="mt-3 font-serif text-3xl leading-[1.15] text-ink dark:text-ink-dark sm:text-4xl">
              A literal translation tells you what it says.
              <br />
              The adapter has to know why it works.
            </h1>
            <p className="mt-4 max-w-prose text-[15px] leading-relaxed text-ink/55 dark:text-ink-dark/55">
              The rhyme a line is chasing, the idiom it's leaning on, the
              thing left unsaid on purpose - a word-for-word pass drops all
              of it. Castia adapts across English, Japanese, Korean,
              Spanish, Urdu, and Hindi, in any direction, and shows its
              work on every line.
            </p>
            <Link
              href="/music"
              className="mt-6 inline-block rounded-full bg-ink px-6 py-2.5 text-[13px] font-medium text-paper transition active:scale-[0.97] dark:bg-ink-dark dark:text-paper-dark"
            >
              Adapt a lyric now
            </Link>
          </div>
          <LyricLineDiagram />
        </div>

        <section className="mt-14">
          <h2 className="font-serif text-xl text-ink dark:text-ink-dark">
            Why literal lyric translation falls short
          </h2>
          <p className="mt-3 max-w-prose text-[14px] leading-relaxed text-ink/60 dark:text-ink-dark/60">
            A song lyric has to satisfy several demands at once - what it
            means, how it sounds, whether it still scans against the
            melody. Translation research on singable lyrics (Peter Low's
            "Pentathlon Principle") names this explicitly: singability,
            sense, naturalness, rhythm, and rhyme all pull against each
            other, and prioritizing literal accuracy above the rest tends
            to produce a translation that's technically correct and
            practically unsingable - or just flat, next to the original.
          </p>
          <p className="mt-3 max-w-prose text-[14px] leading-relaxed text-ink/60 dark:text-ink-dark/60">
            Read more in{" "}
            <Link href="/blog/why-literal-translation-breaks-song-lyrics" className="underline decoration-ink/20 underline-offset-4">
              why literal translation breaks song lyrics
            </Link>
            .
          </p>
        </section>

        <section className="mt-14">
          <h2 className="font-serif text-xl text-ink dark:text-ink-dark">
            Six languages, six different rulebooks
          </h2>
          <p className="mt-3 max-w-prose text-[14px] leading-relaxed text-ink/60 dark:text-ink-dark/60">
            English, Japanese, Korean, Spanish, Urdu, and Hindi don't share
            one notion of what makes a lyric work — each has its own
            language profile encoding what actually carries structure and
            register in that tradition, so the same generic checklist
            isn't applied to all six. A few real examples of what that
            means in practice:
          </p>
          <div className="mt-6 space-y-5">
            <LangNote
              lang="Japanese"
              body='Traditional verse doesn’t rhyme at all — structure comes from mora count against the melody instead, and rhyme in J-pop reads as a consciously borrowed device. The first-person pronoun a singer chooses (僕/boku, 俺/ore, 私/watashi) characterizes their gender and self-presentation before a single image appears, and even script choice is tonal: the same word in hiragana softens it, in katakana it can read as cold or emphatic.'
            />
            <LangNote
              lang="Korean"
              body="Korean grammatically encodes how the speaker regards the listener in the verb ending itself — plain, polite, formal, or written/declarative — and switching mid-song is a real, deliberate event, not a grammar error to normalize away. End rhyme carries little information here since Korean's agglutinative verb endings rhyme almost automatically; meter and repetition do the real structural work instead."
            />
            <LangNote
              lang="Spanish"
              body="Assonant rhyme — matching only the vowels from the last stressed syllable on, ignoring consonants — is a full traditional rhyme form and the backbone of the romance ballad tradition, not a near-miss to be corrected into full rhyme. Diminutives like -ito/-ita are hugely productive and carry affection or condescension, not literal smallness."
            />
            <LangNote
              lang="Urdu & Hindi"
              body="Both sit on the same Persianized-versus-Sanskritized axis from opposite sides: choosing ishq or prem for “love,” mohabbat or pyaar, places a line socially and emotionally in a way a single English word for “love” can't distinguish. The ghazal's radif — a whole phrase repeated verbatim at the end of each couplet — is structural, not incidental, and has to survive adaptation the way a chorus hook does."
            />
          </div>
          <p className="mt-6 max-w-prose text-[14px] leading-relaxed text-ink/60 dark:text-ink-dark/60">
            Every one of these is a real check applied during the Creative
            Adapter and Judge stages of the{" "}
            <Link href="/how-it-works" className="underline decoration-ink/20 underline-offset-4">
              same three-stage pipeline
            </Link>{" "}
            — see it run on a real lyric in the{" "}
            <Link href="/s/demo" className="underline decoration-ink/20 underline-offset-4">
              worked example
            </Link>
            .
          </p>
        </section>

        <section className="mt-14">
          <h2 className="font-serif text-xl text-ink dark:text-ink-dark">
            Supported languages
          </h2>
          <div className="mt-4 flex flex-wrap gap-2">
            {LANGUAGES.map((lang) => (
              <span
                key={lang}
                className="rounded-full border border-black/10 px-3.5 py-1.5 text-[13px] text-ink/65 dark:border-white/10 dark:text-ink-dark/65"
              >
                {lang}
              </span>
            ))}
          </div>
          <p className="mt-4 max-w-prose text-[14px] leading-relaxed text-ink/60 dark:text-ink-dark/60">
            Adapt in any direction between them - Japanese to English,
            Spanish to Korean, Hindi to Urdu, and every other pairing.
          </p>
        </section>

        <p className="mt-14 max-w-prose text-[13px] leading-relaxed text-ink/45 dark:text-ink-dark/45">
          Also localizing comic or webtoon dialogue? See{" "}
          <Link href="/manga-webtoon-translation" className="underline decoration-ink/20 underline-offset-4">
            manga &amp; webtoon translation
          </Link>
          , or check the{" "}
          <Link href="/pricing" className="underline decoration-ink/20 underline-offset-4">
            pricing
          </Link>{" "}
          and{" "}
          <Link href="/faq" className="underline decoration-ink/20 underline-offset-4">
            FAQ
          </Link>
          .
        </p>

        <Footer />
      </div>
    </main>
  );
}

function LangNote({ lang, body }: { lang: string; body: string }) {
  return (
    <div className="border-l-2 border-black/10 pl-5 dark:border-white/10">
      <h3 className="font-serif text-[15px] text-ink dark:text-ink-dark">{lang}</h3>
      <p className="mt-1.5 max-w-prose text-[13.5px] leading-relaxed text-ink/60 dark:text-ink-dark/60">
        {body}
      </p>
    </div>
  );
}

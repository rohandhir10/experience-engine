import { SiteHeader } from "@/components/SiteHeader";
import { Footer } from "@/components/Footer";
import { JsonLd } from "@/components/JsonLd";
import { BreadcrumbNav } from "@/components/BreadcrumbNav";
import Link from "next/link";
import { contentByPath } from "@/lib/content";
import { breadcrumbJsonLd, webPageJsonLd } from "@/lib/schema";

const entry = contentByPath("/lyrics-translation")!;

export const metadata = {
  title: entry.title,
  description: entry.description,
  alternates: { canonical: entry.path },
};

const LANGUAGES = ["English", "Hindi", "Japanese", "Korean", "Spanish", "Urdu"];

export default function LyricsTranslationPage() {
  const breadcrumb = breadcrumbJsonLd([
    { name: "Home", path: "/" },
    { name: "Song lyric translation" },
  ]);
  const webPage = webPageJsonLd({
    path: entry.path,
    name: entry.title,
    description: entry.description,
    updatedDate: entry.updatedDate,
  });

  return (
    <main className="min-h-screen px-6 pb-28 pt-8 sm:px-10">
      <JsonLd data={breadcrumb} />
      <JsonLd data={webPage} />
      <div className="mx-auto max-w-3xl">
        <SiteHeader />

        <div className="mt-10">
          <BreadcrumbNav items={[{ name: "Home", path: "/" }, { name: "Song lyric translation" }]} />
          <h1 className="mt-3 font-serif text-3xl text-ink dark:text-ink-dark sm:text-4xl">
            Translate song lyrics without flattening them.
          </h1>
          <p className="mt-4 max-w-prose text-[15px] leading-relaxed text-ink/55 dark:text-ink-dark/55">
            A literal translation tells you what a lyric says. It rarely
            tells you why the line hits the way it does - the rhyme it's
            chasing, the idiom it's leaning on, the thing left unsaid on
            purpose. Castia adapts across English, Hindi, Japanese, Korean,
            Spanish, and Urdu, in any direction, and shows its work on every
            line.
          </p>
          <Link
            href="/music"
            className="mt-6 inline-block rounded-full bg-ink px-6 py-2.5 text-[13px] font-medium text-paper transition active:scale-[0.97] dark:bg-ink-dark dark:text-paper-dark"
          >
            Adapt a lyric now
          </Link>
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
            English, Hindi, Japanese, Korean, Spanish, and Urdu don't share
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
              lang="Hindi & Urdu"
              body="Both sit on the same Sanskritized-versus-Persianized axis from opposite sides: choosing prem or ishq for “love,” pyaar or mohabbat, places a line socially and emotionally in a way a single English word for “love” can't distinguish. The ghazal's radif — a whole phrase repeated verbatim at the end of each couplet — is structural, not incidental, and has to survive adaptation the way a chorus hook does."
            />
            <LangNote
              lang="Korean"
              body="Korean grammatically encodes how the speaker regards the listener in the verb ending itself — plain, polite, formal, or written/declarative — and switching mid-song is a real, deliberate event, not a grammar error to normalize away. End rhyme carries little information here since Korean's agglutinative verb endings rhyme almost automatically; meter and repetition do the real structural work instead."
            />
            <LangNote
              lang="Spanish"
              body="Assonant rhyme — matching only the vowels from the last stressed syllable on, ignoring consonants — is a full traditional rhyme form and the backbone of the romance ballad tradition, not a near-miss to be corrected into full rhyme. Diminutives like -ito/-ita are hugely productive and carry affection or condescension, not literal smallness."
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
            Spanish to Korean, Urdu to Hindi, and every other pairing.
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

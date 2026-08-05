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
            How Castia adapts a lyric
          </h2>
          <div className="mt-5 space-y-5">
            <Step n="1" title="A literal anchor first" body="The Translator produces one literal reading of the line - not shown as the final output, but the floor every rewrite gets checked against." />
            <Step n="2" title="Five creative rewrites" body="The Creative Adapter produces five differently-angled versions of the same line, each taking a different liberty with phrasing, idiom, or rhythm." />
            <Step n="3" title="A Judge that shows its reasoning" body="The Judge scores each rewrite against the literal anchor, picks a winner, and writes down the specific, real reason it departs from a literal translation - or ships the anchor if none of the five earn their keep." />
          </div>
          <p className="mt-5 max-w-prose text-[14px] leading-relaxed text-ink/60 dark:text-ink-dark/60">
            See the full pipeline on{" "}
            <Link href="/how-it-works" className="underline decoration-ink/20 underline-offset-4">
              how it works
            </Link>
            , or a worked example on the{" "}
            <Link href="/s/demo" className="underline decoration-ink/20 underline-offset-4">
              demo result
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

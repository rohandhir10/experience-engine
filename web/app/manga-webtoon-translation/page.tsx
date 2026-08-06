import { SiteHeader } from "@/components/SiteHeader";
import { Footer } from "@/components/Footer";
import { JsonLd } from "@/components/JsonLd";
import { BreadcrumbNav } from "@/components/BreadcrumbNav";
import { SourceList } from "@/components/SourceList";
import Link from "next/link";
import { contentByPath } from "@/lib/content";
import { breadcrumbJsonLd, articleJsonLd } from "@/lib/schema";

const entry = contentByPath("/manga-webtoon-translation")!;

export const metadata = {
  title: entry.title,
  description: entry.description,
  alternates: { canonical: entry.path },
};

// Same reporting the manga-localization-cost blog post cites - legitimate
// to reuse the citation itself here since this page makes its own,
// different claim from it (a direct cost comparison against Castia's
// own per-page rate), not a restatement of the blog post's prose.
const SOURCES = [
  {
    name: "Publishers Weekly, \"Manga Freelancers Say, 'Show Me the Money'\" (April 26, 2023)",
    url: "https://www.publishersweekly.com/pw/by-topic/industry-news/comics/article/92077-manga-freelancers-say-show-me-the-money.html",
    note: "reported per-chapter freelance translation rates on weekly series",
  },
];

export default function MangaWebtoonTranslationPage() {
  const breadcrumb = breadcrumbJsonLd([
    { name: "Home", path: "/" },
    { name: "Manga & webtoon translation" },
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

        <div className="mt-10">
          <BreadcrumbNav items={[{ name: "Home", path: "/" }, { name: "Manga & webtoon translation" }]} />
          <h1 className="mt-3 font-serif text-3xl text-ink dark:text-ink-dark sm:text-4xl">
            Manga &amp; webtoon translation, panel by panel.
          </h1>
          <p className="mt-4 max-w-prose text-[15px] leading-relaxed text-ink/55 dark:text-ink-dark/55">
            Comic dialogue lives inside speech bubbles baked into the
            artwork, and it has to sound like a specific character talking
            - not a narrator summarizing the scene. Upload a chapter's
            panels, and Castia reads, adapts, and (optionally) redraws and
            re-letters each one. Currently in Beta.
          </p>
          <Link
            href="/comics"
            className="mt-6 inline-block rounded-full bg-ink px-6 py-2.5 text-[13px] font-medium text-paper transition active:scale-[0.97] dark:bg-ink-dark dark:text-paper-dark"
          >
            Try it on a chapter
          </Link>
        </div>

        <section className="mt-14">
          <h2 className="font-serif text-xl text-ink dark:text-ink-dark">
            Bubble text, detected panel by panel
          </h2>
          <p className="mt-3 max-w-prose text-[14px] leading-relaxed text-ink/60 dark:text-ink-dark/60">
            Each panel goes through Google Cloud Vision OCR, which detects
            every speech bubble's text and its position, so nothing needs
            to be manually transcribed before adaptation can start. A
            Chapter DNA pass then reads the whole chapter and builds a
            cast-and-tone profile — who's speaking, how each character
            speaks, the tone of each scene — so a character's voice stays
            consistent from the first panel to the last instead of being
            re-decided line by line with no memory of what came before.
          </p>
          <p className="mt-3 max-w-prose text-[14px] leading-relaxed text-ink/60 dark:text-ink-dark/60">
            Reading order is inferred from where each bubble sits, so the
            same detection pass handles a manga spread read right to left
            and a webtoon strip read top to bottom. Without a dedicated
            text-detector service configured, the fallback ordering is a
            plain top-to-bottom guess — this is one of the specific rough
            edges the Beta label refers to, not a general disclaimer.
          </p>
        </section>

        <section className="mt-14">
          <h2 className="font-serif text-xl text-ink dark:text-ink-dark">
            Dialogue runs through the full Writers' Room
          </h2>
          <p className="mt-3 max-w-prose text-[14px] leading-relaxed text-ink/60 dark:text-ink-dark/60">
            Once the dialogue is read, every line goes through the
            identical Translator → Creative Adapter → Judge pipeline the
            music side uses: a literal anchor, five creative rewrites, and
            a Judge that picks a winner and states its reason for departing
            from a literal reading — with the Chapter DNA cast profile
            injected into the prompt for each character's lines, so the
            same character's voice doesn't drift between their first line
            and their fifteenth. See the full mechanics on{" "}
            <Link href="/how-it-works" className="underline decoration-ink/20 underline-offset-4">
              how it works
            </Link>
            .
          </p>
        </section>

        <section className="mt-14">
          <h2 className="font-serif text-xl text-ink dark:text-ink-dark">
            What Beta actually means here
          </h2>
          <p className="mt-3 max-w-prose text-[14px] leading-relaxed text-ink/60 dark:text-ink-dark/60">
            Save, collections, and share-links work the same way they do
            for music — that part isn't the Beta gap. Two things
            specifically aren't finished: sound-effect text drawn directly
            into the artwork isn't redrawn, only speech-bubble text is; and
            reading order falls back to a plain top-to-bottom guess unless
            a dedicated text-detector service is configured, as noted
            above. Both are tracked openly rather than smoothed over in the
            marketing.
          </p>
        </section>

        <section className="mt-14">
          <h2 className="font-serif text-xl text-ink dark:text-ink-dark">
            Optional redraw &amp; typeset
          </h2>
          <p className="mt-3 max-w-prose text-[14px] leading-relaxed text-ink/60 dark:text-ink-dark/60">
            A redraw step can erase the original lettering from a panel -
            inpainting the artwork underneath it - and typeset the adapted
            line back in, sized and wrapped to fit the bubble. This is the
            same erase-and-reletter work a professional letterer does by
            hand; Castia automates it as an optional pass, not a
            replacement for a full professional pipeline on something
            high-stakes.
          </p>
          <p className="mt-3 max-w-prose text-[14px] leading-relaxed text-ink/60 dark:text-ink-dark/60">
            Publishers Weekly's 2023 reporting on freelance manga
            translators organizing over pay described rates in the
            neighborhood of $100-250 per chapter on weekly series — that's
            translation alone, before typesetting and lettering are
            factored in separately. At Starter-pack rates, a full page here
            — translated, redrawn, and typeset — runs about $3.50 (see{" "}
            <Link href="/pricing" className="underline decoration-ink/20 underline-offset-4">
              pricing
            </Link>
            ), which is why it's positioned as a fast first pass for
            high-volume work, not a professional pipeline replacement on
            something high-stakes. Full context on those industry figures
            is in{" "}
            <Link href="/blog/what-manga-localization-actually-costs" className="underline decoration-ink/20 underline-offset-4">
              what manga and webtoon localization actually costs
            </Link>
            .
          </p>
        </section>

        <SourceList sources={SOURCES} />

        <p className="mt-14 max-w-prose text-[13px] leading-relaxed text-ink/45 dark:text-ink-dark/45">
          Working with song lyrics instead? See{" "}
          <Link href="/lyrics-translation" className="underline decoration-ink/20 underline-offset-4">
            song lyric translation
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

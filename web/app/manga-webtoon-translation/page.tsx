import { SiteHeader } from "@/components/SiteHeader";
import { Footer } from "@/components/Footer";
import { JsonLd } from "@/components/JsonLd";
import { BreadcrumbNav } from "@/components/BreadcrumbNav";
import Link from "next/link";
import { contentByPath } from "@/lib/content";
import { breadcrumbJsonLd, webPageJsonLd } from "@/lib/schema";

const entry = contentByPath("/manga-webtoon-translation")!;

export const metadata = {
  title: entry.title,
  description: entry.description,
  alternates: { canonical: entry.path },
};

export default function MangaWebtoonTranslationPage() {
  const breadcrumb = breadcrumbJsonLd([
    { name: "Home", path: "/" },
    { name: "Manga & webtoon translation" },
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
            Real OCR, not a manual transcript
          </h2>
          <p className="mt-3 max-w-prose text-[14px] leading-relaxed text-ink/60 dark:text-ink-dark/60">
            Each panel goes through Google Cloud Vision OCR to detect and
            read every speech bubble's text and position, so nothing needs
            to be manually transcribed before adaptation can start. A
            Chapter DNA pass then builds a cast-and-tone profile for the
            whole chapter, so a character's voice stays consistent from the
            first panel to the last - not re-decided line by line with no
            memory of what came before.
          </p>
        </section>

        <section className="mt-14">
          <h2 className="font-serif text-xl text-ink dark:text-ink-dark">
            The same Writers' Room, not a lesser engine
          </h2>
          <p className="mt-3 max-w-prose text-[14px] leading-relaxed text-ink/60 dark:text-ink-dark/60">
            Once the dialogue is read, it goes through the identical
            Translator → Creative Adapter → Judge pipeline the music side
            uses: a literal anchor, five creative rewrites, and a Judge
            that picks a winner and states its reason for departing from a
            literal reading. See the full mechanics on{" "}
            <Link href="/how-it-works" className="underline decoration-ink/20 underline-offset-4">
              how it works
            </Link>
            .
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
            For where this fits next to real industry rates and workflow,
            see{" "}
            <Link href="/blog/what-manga-localization-actually-costs" className="underline decoration-ink/20 underline-offset-4">
              what manga and webtoon localization actually costs
            </Link>
            .
          </p>
        </section>

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

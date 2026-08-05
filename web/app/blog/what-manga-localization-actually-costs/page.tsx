import Link from "next/link";
import { BlogPostShell } from "@/components/BlogPostShell";
import { contentByPath } from "@/lib/content";

const entry = contentByPath("/blog/what-manga-localization-actually-costs")!;

export const metadata = {
  title: entry.title,
  description: entry.description,
  alternates: { canonical: entry.path },
};

const SOURCES = [
  {
    name: "Publishers Weekly, \"Manga Freelancers Say, 'Show Me the Money'\" (April 26, 2023)",
    url: "https://www.publishersweekly.com/pw/by-topic/industry-news/comics/article/92077-manga-freelancers-say-show-me-the-money.html",
    note: "reported per-chapter and per-page freelance translation rates and the push for higher pay",
  },
  {
    name: "Anime News Network, \"Translation, Typesetting Company Amimaru Issues Statement Regarding Low Pay Rates\" (August 29, 2020)",
    url: "https://www.animenewsnetwork.com/news/2020-08-29/translation-typesetting-company-amimaru-issues-statement-regarding-low-pay-rates/.163440",
    note: "reported per-page typesetting/lettering rates, distinct from translation",
  },
  {
    name: "Anime News Network, \"Comics Publisher INKR Issues Statement on Translation Rates\" (February 2, 2021)",
    url: "https://www.animenewsnetwork.com/interest/2021-02-02/comics-publisher-inkr-issues-statement-on-translation-rates/.169035",
    note: "reported per-character translation rate and industry-average framing",
  },
];

export default function Post() {
  return (
    <BlogPostShell
      entry={entry}
      citations={SOURCES}
      cta={{
        heading: "See a first pass on a real chapter.",
        body: "Upload panels and get OCR, adaptation, and optional redraw - a fast starting point, not a replacement for a professional pipeline.",
        href: "/comics",
        label: "Try it on a chapter",
      }}
    >
      <p className="max-w-prose text-[14px] leading-relaxed text-ink/65 dark:text-ink-dark/65">
        Manga and webtoon localization is a real, skilled, two-stage
        industry - translation, then typesetting and lettering - and it's
        one that has been publicly and repeatedly reported as underpaid.
        Understanding what that professional pipeline actually costs is
        the honest way to talk about where an automated first pass fits,
        and where it doesn't.
      </p>

      <h2 className="font-serif text-xl text-ink dark:text-ink-dark">
        Two jobs, not one
      </h2>
      <p className="max-w-prose text-[14px] leading-relaxed text-ink/65 dark:text-ink-dark/65">
        Translating the dialogue and typesetting/lettering it back into
        the art are separate skills, usually done by separate people.
        Reporting from Anime News Network on the typesetting/lettering
        company Amimaru's 2020 statement about its own pay practices
        described per-page rates for that lettering work reported in the
        low single dollars per page - separate from, and in addition to,
        whatever the translation itself cost.
      </p>

      <h2 className="font-serif text-xl text-ink dark:text-ink-dark">
        What translators have publicly said they're paid
      </h2>
      <p className="max-w-prose text-[14px] leading-relaxed text-ink/65 dark:text-ink-dark/65">
        Publishers Weekly's 2023 reporting, "Manga Freelancers Say, 'Show
        Me the Money,'" covered freelance manga translators organizing
        (forming the United Workers of Seven Seas with the Communications
        Workers of America) over rates they described as roughly $100-250
        per chapter on weekly series, or in the neighborhood of
        $1,000-1,700 per month on monthly series - figures the reporting
        traced back to a rate cut following the manga market's 2007-2008
        boom-and-bust that publishers were reported to have been slow to
        reverse, before those specific organizing efforts pushed rates up
        at some publishers. Separately, Anime News Network's 2021
        reporting on the comics publisher INKR quoted the company
        acknowledging a rate of roughly one cent per character for
        Japanese-to-English translation, which it stated it had since
        moved toward an "industry average."
      </p>
      <p className="max-w-prose text-[14px] leading-relaxed text-ink/65 dark:text-ink-dark/65">
        These are the specific numbers that were publicly reported at the
        time - worth clicking through to the original reporting below
        before quoting them elsewhere, since rates like these are
        contested and do shift.
      </p>

      <h2 className="font-serif text-xl text-ink dark:text-ink-dark">
        Where an automated pass actually fits
      </h2>
      <p className="max-w-prose text-[14px] leading-relaxed text-ink/65 dark:text-ink-dark/65">
        None of this makes the case that automation should replace a paid
        professional pipeline on a commercial release - the reporting
        above is, if anything, an argument that the people doing this work
        are already underpaid, not a case for paying them less or not at
        all. What it does support is a narrower, honest claim: a fast,
        automated first pass - OCR to read the panels, an adapted draft of
        the dialogue with a stated reason for each creative choice, and an
        optional redraw of the lettering - is a useful starting point for
        a hobbyist, a fan project, or a professional's first draft, the
        same way machine-translation post-editing (MTPE) is an established
        way to combine MT speed with human review rather than a
        replacement for the human. See{" "}
        <Link href="/manga-webtoon-translation" className="underline decoration-ink/20 underline-offset-4">
          manga &amp; webtoon translation
        </Link>{" "}
        for how that first pass actually works.
      </p>
    </BlogPostShell>
  );
}

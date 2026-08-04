import Link from "next/link";
import { SiteHeader } from "@/components/SiteHeader";
import { SystemComparisonCard } from "@/components/SystemComparisonCard";
import { comparisonEntries, methodologyNote } from "@/lib/comparison-data";
import { LANGUAGES } from "@/lib/languages";

export const metadata = {
  title: "AURA — Compare",
  description:
    "The same source lyric, run through Google Translate, a single GPT prompt, and AURA, side by side.",
};

export default function ComparePage() {
  return (
    <main className="min-h-screen px-6 pb-28 pt-8 sm:px-10">
      <div className="mx-auto max-w-3xl">
        <SiteHeader
          active="compare"
          right={
            <Link
              href="/"
              className="text-[13px] text-ink/45 transition hover:text-ink/70 dark:text-ink-dark/45 dark:hover:text-ink-dark/70"
            >
              ← Try your own
            </Link>
          }
        />

        <div className="mt-10">
          <h1 className="font-serif text-3xl text-ink dark:text-ink-dark sm:text-4xl">
            See the difference.
          </h1>
          <p className="mt-4 max-w-prose text-[15px] leading-relaxed text-ink/55 dark:text-ink-dark/55">
            {methodologyNote}
          </p>
          {/* The one entry below happens to be a Hindi/Punjabi song -
              that's which benchmark run has been through the full
              Google-Translate/GPT/AURA comparison so far
              (benchmark/README.md), not a statement about which
              languages this tool is for. Named explicitly so a single
              example doesn't stand in for the whole language matrix. */}
          <p className="mt-3 max-w-prose text-[13px] leading-relaxed text-ink/40 dark:text-ink-dark/40">
            AURA adapts between any two of {LANGUAGES.join(", ")} — the
            example below is the one benchmark run completed so far, not
            the limit of what it does.
          </p>
        </div>

        <div className="mt-12 space-y-14">
          {comparisonEntries.map((entry) => (
            <section key={entry.songId}>
              <div className="flex items-baseline justify-between gap-4">
                <h2 className="font-serif text-xl text-ink dark:text-ink-dark sm:text-2xl">
                  {entry.title}
                </h2>
                <span className="text-[12px] uppercase tracking-[0.1em] text-ink/35 dark:text-ink-dark/35">
                  {entry.sourceLanguage}
                </span>
              </div>
              <p className="mt-2 max-w-prose text-[13px] leading-relaxed text-ink/40 dark:text-ink-dark/40">
                {entry.provenance}
              </p>
              <div className="mt-6 space-y-6">
                {entry.sections.map((section, i) => (
                  <SystemComparisonCard key={section.id} section={section} index={i} />
                ))}
              </div>
            </section>
          ))}
        </div>
      </div>
    </main>
  );
}

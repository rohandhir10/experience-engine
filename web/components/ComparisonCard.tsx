import { forwardRef, useState } from "react";
import type { SectionComparison } from "@/lib/types";
import { LoreStoryline } from "./LoreStoryline";
import { DeviationText } from "./DeviationText";

function humanize(id: string): string {
  const cleaned = id.replace(/_/g, " ").trim();
  return cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      title="Copy the CASTIA lyrics for this section"
      onClick={async () => {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      }}
      className="flex h-8 w-8 items-center justify-center rounded-full border border-black/[0.10] text-ink/62 transition hover:border-black/[0.15] hover:text-ink/78 dark:border-white/[0.12] dark:text-ink-dark/62 dark:hover:border-white/[0.15] dark:hover:text-ink-dark/78"
    >
      {copied ? (
        <span className="text-[10px] font-medium">✓</span>
      ) : (
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
          <rect x="8" y="8" width="12" height="12" rx="2" />
          <path d="M4 16V6a2 2 0 0 1 2-2h10" />
        </svg>
      )}
    </button>
  );
}

export const ComparisonCard = forwardRef<
  HTMLDivElement,
  {
    section: SectionComparison;
    index: number;
    original?: string;
    showOriginal?: boolean;
    active?: boolean;
    // Song-level - only pass this for one card (ResultScreen passes it
    // on index 0) so it doesn't repeat under every section.
    poeticRegister?: string | null;
  }
>(function ComparisonCard(
  { section, index, original, showOriginal, active, poeticRegister },
  ref
) {
  return (
    <div
      ref={ref}
      data-screenshot={index === 0 ? "comparison-card" : undefined}
      className={`animate-fade-up relative rounded-2xl border px-7 py-8 transition-colors sm:px-10 sm:py-10 ${
        active
          ? "border-accent/40 bg-accent/[0.03]"
          : "border-black/[0.10] dark:border-white/[0.11]"
      }`}
      style={{ animationDelay: `${index * 90}ms` }}
    >
      <div className="flex items-start justify-between">
        <p className="text-xs font-medium uppercase tracking-[0.15em] text-ink/62 dark:text-ink-dark/62">
          {humanize(section.id)}
        </p>
        <CopyButton text={section.aura} />
      </div>

      {showOriginal && original && (
        <div className="mt-6 space-y-1 border-b border-black/[0.09] pb-6 dark:border-white/[0.09]">
          <p className="text-[11px] font-medium uppercase tracking-[0.15em] text-ink/65 dark:text-ink-dark/65">
            Original
          </p>
          <p className="max-w-prose whitespace-pre-line text-[15px] leading-relaxed text-ink/62 dark:text-ink-dark/62">
            {original}
          </p>
        </div>
      )}

      <div className="mt-7 grid grid-cols-1 gap-8 md:grid-cols-2 md:divide-x md:divide-black/[0.10] md:dark:divide-white/[0.11]">
        <div className="space-y-2 md:pr-8">
          <span className="inline-flex items-center rounded-md border border-black/[0.13] px-2 py-0.5 text-[10px] font-medium uppercase tracking-[0.15em] text-ink/62 dark:border-white/[0.15] dark:text-ink-dark/62">
            [ Literal ]
          </span>
          <p className="max-w-prose whitespace-pre-line text-[15px] leading-relaxed text-ink/75 dark:text-ink-dark/75">
            {section.literal}
          </p>
        </div>

        <div className="space-y-2 md:pl-8">
          <span
            className="inline-flex items-center rounded-full bg-accent/10 px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-[0.15em] text-accent"
          >
            Castia
          </span>
          <p className="max-w-prose font-serif text-[19px] leading-relaxed text-ink dark:text-ink-dark sm:text-[21px]">
            <DeviationText text={section.aura} deviations={section.deviations} why={section.why} />
          </p>
        </div>
      </div>

      <p className="mt-8 max-w-prose text-[14px] italic leading-relaxed text-ink/68 dark:text-ink-dark/68">
        {section.why}
      </p>

      <LoreStoryline poeticRegister={poeticRegister} dominantFeeling={section.dominantFeeling} />

      {section.singability && (
        <div className="mt-5 flex flex-wrap gap-2 border-t border-black/[0.09] pt-5 dark:border-white/[0.09]">
          <span
            className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] ${
              section.singability.closeMatch
                ? "bg-black/[0.03] text-ink/75 dark:bg-white/[0.04] dark:text-ink-dark/75"
                : "bg-black/[0.03] text-ink/78 dark:bg-white/[0.04] dark:text-ink-dark/78"
            }`}
          >
            <span aria-hidden>♪</span>
            {section.singability.closeMatch
              ? `${section.singability.shippedCount} syllables · matches source pacing`
              : `${section.singability.shippedCount} vs ${section.singability.sourceCount} syllables · pacing may shift`}
          </span>
        </div>
      )}
    </div>
  );
});

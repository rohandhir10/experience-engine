import type { SectionComparison } from "@/lib/types";

function humanize(id: string): string {
  const cleaned = id.replace(/_/g, " ").trim();
  return cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
}

export function ComparisonCard({
  section,
  index,
  original,
  showOriginal,
}: {
  section: SectionComparison;
  index: number;
  original?: string;
  showOriginal?: boolean;
}) {
  return (
    <div
      className="animate-fade-up relative rounded-2xl border border-black/[0.06] px-7 py-8 dark:border-white/[0.07] sm:px-10 sm:py-10"
      style={{ animationDelay: `${index * 90}ms` }}
    >
      <p className="text-xs font-medium uppercase tracking-[0.15em] text-ink/40 dark:text-ink-dark/40">
        {humanize(section.id)}
      </p>

      {showOriginal && original && (
        <div className="mt-6 space-y-1 border-b border-black/[0.05] pb-6 dark:border-white/[0.05]">
          <p className="text-[11px] font-medium uppercase tracking-[0.15em] text-ink/30 dark:text-ink-dark/30">
            Original
          </p>
          <p className="max-w-prose whitespace-pre-line text-[15px] leading-relaxed text-ink/40 dark:text-ink-dark/40">
            {original}
          </p>
        </div>
      )}

      <div className="mt-6 space-y-1">
        <p className="text-[11px] font-medium uppercase tracking-[0.15em] text-ink/30 dark:text-ink-dark/30">
          Literal
        </p>
        <p className="max-w-prose whitespace-pre-line text-[15px] leading-relaxed text-ink/45 dark:text-ink-dark/45">
          {section.literal}
        </p>
      </div>

      <div className="my-8 flex justify-center">
        <span className="text-[13px] leading-none text-accent/50">↓</span>
      </div>

      <div className="space-y-1">
        <p className="text-[11px] font-medium uppercase tracking-[0.15em] text-ink/40 dark:text-ink-dark/40">
          AURA
        </p>
        <p className="max-w-prose whitespace-pre-line font-serif text-[19px] leading-relaxed text-ink dark:text-ink-dark sm:text-[21px]">
          {section.aura}
        </p>
      </div>

      <p className="mt-6 max-w-prose text-[14px] italic leading-relaxed text-ink/50 dark:text-ink-dark/50">
        {section.why}
      </p>

      <span className="pointer-events-none absolute bottom-6 right-7 text-[10px] font-medium tracking-[0.25em] text-ink/[0.12] dark:text-ink-dark/[0.12] sm:right-10">
        AURA
      </span>
    </div>
  );
}

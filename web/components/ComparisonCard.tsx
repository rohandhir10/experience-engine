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
      className="animate-fade-up relative rounded-2xl border border-black/[0.06] bg-white/60 px-7 py-8 shadow-[0_1px_2px_rgba(0,0,0,0.04)] backdrop-blur-sm dark:border-white/[0.06] dark:bg-white/[0.03] sm:px-10 sm:py-10"
      style={{ animationDelay: `${index * 90}ms` }}
    >
      <span className="pointer-events-none absolute right-6 top-6 text-[10px] font-medium tracking-[0.25em] text-ink/20 dark:text-ink-dark/20">
        AURA
      </span>

      <p className="mb-6 text-xs font-medium uppercase tracking-[0.15em] text-ink/40 dark:text-ink-dark/40">
        {humanize(section.id)}
      </p>

      {showOriginal && original && (
        <div className="mb-6 space-y-1 border-b border-black/[0.05] pb-6 dark:border-white/[0.05]">
          <p className="text-[11px] font-medium uppercase tracking-[0.15em] text-ink/30 dark:text-ink-dark/30">
            Original
          </p>
          <p className="max-w-prose whitespace-pre-line text-[15px] leading-relaxed text-ink/40 dark:text-ink-dark/40">
            {original}
          </p>
        </div>
      )}

      <div className="space-y-1">
        <p className="text-[11px] font-medium uppercase tracking-[0.15em] text-ink/30 dark:text-ink-dark/30">
          Literal
        </p>
        <p className="max-w-prose whitespace-pre-line text-[15px] leading-relaxed text-ink/45 dark:text-ink-dark/45">
          {section.literal}
        </p>
      </div>

      <div className="my-6 flex items-center gap-3 text-ink/20 dark:text-ink-dark/20">
        <span className="h-px flex-1 bg-current opacity-30" />
        <span className="text-sm">↓</span>
        <span className="h-px flex-1 bg-current opacity-30" />
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
    </div>
  );
}

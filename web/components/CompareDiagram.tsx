// Original artwork, not a screenshot - visualizes the real, specific
// contrast each /compare page's own prose already makes: the competitor
// takes one documented pass and returns it, Castia runs a literal anchor
// through five creative rewrites and a Judge before one ships. Shared
// across the three /compare/* pages so the comparison reads as one
// consistent claim, not three differently-decorated restatements of it.
export function CompareDiagram({
  competitorName,
  competitorStep,
}: {
  competitorName: string;
  competitorStep: string;
}) {
  return (
    <div className="rounded-2xl border border-black/[0.08] bg-paper p-6 dark:border-white/[0.08] dark:bg-paper-dark sm:p-7">
      <p className="text-[10px] font-medium uppercase tracking-[0.1em] text-ink/35 dark:text-ink-dark/35">
        {competitorName}
      </p>
      <div className="mt-2.5 flex items-center gap-2.5">
        <span className="rounded-lg border border-ink/15 px-3 py-2 text-[12.5px] text-ink/70 dark:border-ink-dark/15 dark:text-ink-dark/70">
          {competitorStep}
        </span>
        <span className="text-ink/25 dark:text-ink-dark/25" aria-hidden="true">
          →
        </span>
        <span className="rounded-lg bg-ink/5 px-3 py-2 text-[12.5px] text-ink/50 dark:bg-ink-dark/10 dark:text-ink-dark/50">
          Output
        </span>
      </div>

      <div className="my-5 border-t border-dashed border-black/10 dark:border-white/10" />

      <p className="text-[10px] font-medium uppercase tracking-[0.1em] text-accent/70">
        Castia
      </p>
      <div className="mt-2.5 flex flex-wrap items-center gap-2 gap-y-2.5">
        <span className="rounded-lg border border-ink/15 px-2.5 py-1.5 text-[11.5px] text-ink/70 dark:border-ink-dark/15 dark:text-ink-dark/70">
          Literal anchor
        </span>
        <span className="text-ink/25 dark:text-ink-dark/25" aria-hidden="true">
          →
        </span>
        <span className="rounded-lg border border-ink/15 px-2.5 py-1.5 text-[11.5px] text-ink/70 dark:border-ink-dark/15 dark:text-ink-dark/70">
          5 rewrites
        </span>
        <span className="text-ink/25 dark:text-ink-dark/25" aria-hidden="true">
          →
        </span>
        <span className="rounded-lg bg-accent px-2.5 py-1.5 text-[11.5px] font-medium text-paper">
          Judge
        </span>
        <span className="text-ink/25 dark:text-ink-dark/25" aria-hidden="true">
          →
        </span>
        <span className="rounded-lg bg-ink/5 px-2.5 py-1.5 text-[11.5px] text-ink/50 dark:bg-ink-dark/10 dark:text-ink-dark/50">
          Output
        </span>
      </div>
    </div>
  );
}

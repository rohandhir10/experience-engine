const STAGES: { title: string; description: string }[] = [
  { title: "Source lyrics", description: "Original language, any of six" },
  { title: "Translator", description: "A literal anchor — the floor everything else diffs against" },
  { title: "Creative Adapter", description: "Five candidates, one per adaptation philosophy" },
  { title: "Judge", description: "Rules against the anchor, logs every real deviation with a reason" },
  { title: "Verified output", description: "Checked against the anchor before it ships" },
];

/** The real Writers' Room pipeline (docs/WRITERS_ROOM_V1.md), as an
 * honest architecture diagram rather than a screenshot - there's no UI
 * surface that shows this directly, since it's server-side, so a
 * diagram is the accurate way to show it, not a gap being covered for. */
export function PipelineDiagram() {
  return (
    <div className="flex flex-col items-stretch gap-3 sm:flex-row sm:items-center sm:gap-0">
      {STAGES.map((stage, i) => (
        <div key={stage.title} className="flex flex-1 items-center gap-0">
          <div className="flex-1 rounded-xl border border-black/[0.12] bg-white/70 p-4 dark:border-white/[0.12] dark:bg-white/[0.03]">
            <p className="text-[13px] font-medium text-ink dark:text-ink-dark">{stage.title}</p>
            <p className="mt-1 text-[11px] leading-relaxed text-ink/45 dark:text-ink-dark/45">
              {stage.description}
            </p>
          </div>
          {i < STAGES.length - 1 && (
            <span
              className="hidden shrink-0 px-2 text-ink/20 sm:block dark:text-ink-dark/20"
              aria-hidden="true"
            >
              →
            </span>
          )}
        </div>
      ))}
    </div>
  );
}

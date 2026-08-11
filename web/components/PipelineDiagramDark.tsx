const STAGES: { title: string; description: string }[] = [
  { title: "Source lyrics", description: "Original language, any of six" },
  { title: "Translator", description: "A literal anchor — the floor everything else diffs against" },
  { title: "Creative Adapter", description: "Five candidates, one per adaptation philosophy" },
  { title: "Judge", description: "Rules against the anchor, logs every real deviation with a reason" },
  { title: "Verified output", description: "Checked against the anchor before it ships" },
];

/** Same real Writers' Room pipeline (docs/WRITERS_ROOM_V1.md) as
 * components/PipelineDiagram.tsx, restyled dark/cinematic for /music's
 * forced-dark shell (InputScreen.tsx) rather than that component's
 * theme-adaptive card styling, which still serves app/alternate-
 * homepage/page.tsx unchanged. Duplicated rather than parameterized -
 * two small, different-purpose components are simpler to reason about
 * than one component branching on a forceDark prop for five list items.
 * The connecting line's traveling dot is decorative motion only - reads
 * as "an active engine," not a claim about real per-request telemetry. */
export function PipelineDiagramDark() {
  return (
    <div className="flex flex-col items-stretch gap-3 sm:flex-row sm:items-stretch sm:gap-0">
      {STAGES.map((stage, i) => (
        <div key={stage.title} className="flex flex-1 items-center gap-0">
          <div className="flex-1 rounded-xl border border-white/10 bg-white/[0.03] p-4">
            <p className="text-[13px] font-medium text-white/90">{stage.title}</p>
            <p className="mt-1 text-[11px] leading-relaxed text-white/62">
              {stage.description}
            </p>
          </div>
          {i < STAGES.length - 1 && (
            <div
              className="relative hidden h-px w-8 shrink-0 bg-white/10 sm:block"
              aria-hidden="true"
            >
              <span
                className="animate-travel-dot absolute -top-[3px] h-[7px] w-[7px] rounded-full bg-accent shadow-[0_0_6px_rgba(124,124,255,0.8)]"
                style={{ animationDelay: `${i * 0.4}s` }}
              />
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

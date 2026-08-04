const STAGES: { title: string; description: string }[] = [
  { title: "Panel upload", description: "One image per panel, in reading order" },
  { title: "OCR", description: "Google Cloud Vision reads each bubble's text and position" },
  { title: "Chapter DNA", description: "Genre, tone, and cast profile for the whole chapter" },
  { title: "Writers' Room", description: "The same Translator → Adapter → Judge pipeline as music" },
  { title: "Adapted script", description: "Literal, adapted line, and why — per panel" },
];

/** The real comics pipeline, honestly labeled - deliberately not the
 * "OCR & Vision Agent → Adversarial Translation Pipeline → Typesetting
 * Agent" framing from the original landing-page brief, which named two
 * things that don't exist (there's no adversarial mechanism, and
 * typesetting is a separate, optional step - see engine/
 * comics_redraw.py - not a stage every chapter runs through). Dark and
 * cinematic on purpose even though /comics itself is a light-themed
 * page - a deliberately technical, "under the hood" section breaking
 * the page's own theme for weight, same pattern components/
 * PipelineDiagramDark.tsx uses on /music. The connecting line's
 * traveling dot is decorative motion only. */
export function ComicsPipelineDiagram() {
  return (
    <div className="flex flex-col items-stretch gap-3 sm:flex-row sm:items-stretch sm:gap-0">
      {STAGES.map((stage, i) => (
        <div key={stage.title} className="flex flex-1 items-center gap-0">
          <div className="flex-1 rounded-xl border border-white/10 bg-white/[0.03] p-4">
            <p className="text-[13px] font-medium text-white/90">{stage.title}</p>
            <p className="mt-1 text-[11px] leading-relaxed text-white/40">
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

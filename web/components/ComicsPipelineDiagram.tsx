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
 * comics_redraw.py - not a stage every chapter runs through). The
 * connecting line's traveling dot is decorative motion only.
 *
 * `dark` (default true, same "explicit opt-out" convention as
 * Footer/TargetLanguageSelect's own `dark` prop) forces the always-white-
 * on-navy styling this component originally shipped with - real
 * dark-mode-only usages against a fixed dark wrapper, e.g. app/how-it-
 * works/page.tsx's `bg-[#141a2b]` card, need internal text that's always
 * legible against THAT specific fixed background regardless of the
 * site's own light/dark setting, not classes that would swap to
 * dark-mode-styled (light) text the moment a visitor's site theme
 * doesn't match the wrapper's fixed color.
 *
 * `dark={false}` (app/comics/page.tsx) is the fix for a real, reported
 * problem: /comics itself is a normal theme-reactive light/dark page,
 * and wrapping this diagram in that same fixed dark navy card put one
 * lone dark rectangle against /comics's plain light background in light
 * mode - exactly the "mismatched, templated" look a genuinely intentional
 * design choice shouldn't produce. how-it-works's own dark treatment
 * reads differently there specifically because it's paired with an
 * identical dark "Music" card directly above it (PipelineDiagramDark) -
 * a deliberate two-card rhythm, not a single card standing out alone -
 * so that usage keeps the old default rather than needing this fix too. */
export function ComicsPipelineDiagram({ dark = true }: { dark?: boolean }) {
  return (
    <div className="flex flex-col items-stretch gap-3 sm:flex-row sm:items-stretch sm:gap-0">
      {STAGES.map((stage, i) => (
        <div key={stage.title} className="flex flex-1 items-center gap-0">
          <div
            className={
              dark
                ? "flex-1 rounded-xl border border-white/10 bg-white/[0.03] p-4"
                : "flex-1 rounded-xl border border-black/[0.08] bg-black/[0.02] p-4 dark:border-white/10 dark:bg-white/[0.03]"
            }
          >
            <p className={dark ? "text-[13px] font-medium text-white/90" : "text-[13px] font-medium text-ink dark:text-white/90"}>
              {stage.title}
            </p>
            <p
              className={
                dark
                  ? "mt-1 text-[11px] leading-relaxed text-white/40"
                  : "mt-1 text-[11px] leading-relaxed text-ink/50 dark:text-white/40"
              }
            >
              {stage.description}
            </p>
          </div>
          {i < STAGES.length - 1 && (
            <div
              className={
                dark
                  ? "relative hidden h-px w-8 shrink-0 bg-white/10 sm:block"
                  : "relative hidden h-px w-8 shrink-0 bg-black/10 dark:bg-white/10 sm:block"
              }
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

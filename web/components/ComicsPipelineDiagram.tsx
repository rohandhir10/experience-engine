import type { JSX } from "react";
function UploadIcon() {
  return (
    <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 15V4M8 8l4-4 4 4" />
      <path d="M4 15v2a3 3 0 0 0 3 3h10a3 3 0 0 0 3-3v-2" />
    </svg>
  );
}

function EyeIcon() {
  return (
    <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7-10-7-10-7Z" />
      <circle cx="12" cy="12" r="2.5" />
    </svg>
  );
}

function SlidersIcon() {
  return (
    <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <line x1="4" y1="6" x2="20" y2="6" />
      <circle cx="9" cy="6" r="2" />
      <line x1="4" y1="12" x2="20" y2="12" />
      <circle cx="15" cy="12" r="2" />
      <line x1="4" y1="18" x2="20" y2="18" />
      <circle cx="7" cy="18" r="2" />
    </svg>
  );
}

function PenIcon() {
  return (
    <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 20h9" />
      <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 6 9 17l-5-5" />
    </svg>
  );
}

const STAGES: { title: string; description: string; Icon: () => JSX.Element }[] = [
  { title: "Panel upload", description: "One image per panel, in reading order", Icon: UploadIcon },
  { title: "OCR", description: "Google Cloud Vision reads each bubble's text and position", Icon: EyeIcon },
  { title: "Chapter DNA", description: "Genre, tone, and cast profile for the whole chapter", Icon: SlidersIcon },
  { title: "Writers' Room", description: "The same Translator → Adapter → Judge pipeline as music", Icon: PenIcon },
  { title: "Adapted script", description: "Literal, adapted line, and why — per panel", Icon: CheckIcon },
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
 * so that usage keeps the old default rather than needing this fix too.
 *
 * The first `dark={false}` pass just inverted the dark palette to
 * near-white-on-white (bg-black/[0.02], border-black/[0.12]) - correct
 * on contrast, but flat and characterless next to the dark version's
 * white-on-navy presence. A numbered accent badge per stage plus a
 * warmer per-card surface fixed that; per-step icons (this pass) replace
 * the numeral inside that same badge, since "which of five nearly-
 * identical text blocks am I reading" is exactly what a visual anchor
 * fixes and a numeral doesn't. Both changes stay behind `!dark` so
 * how-it-works's paired dark cards - which need to stay pixel-identical,
 * per the reasoning above - are untouched by construction. */
export function ComicsPipelineDiagram({ dark = true }: { dark?: boolean }) {
  return (
    <div className="flex flex-col items-stretch gap-3 sm:flex-row sm:items-stretch sm:gap-0">
      {STAGES.map((stage, i) => (
        <div key={stage.title} className="flex flex-1 items-center gap-0">
          <div
            className={
              dark
                ? "flex-1 rounded-xl border border-white/10 bg-white/[0.03] p-4"
                : "flex-1 rounded-xl border border-black/[0.12] bg-white p-4 shadow-[0_1px_2px_rgba(0,0,0,0.04)] dark:border-white/10 dark:bg-white/[0.03] dark:shadow-none"
            }
          >
            {!dark && (
              <span className="mb-2.5 inline-flex h-7 w-7 items-center justify-center rounded-full bg-accent/10 text-accent dark:hidden">
                <stage.Icon />
              </span>
            )}
            <p className={dark ? "text-[13px] font-medium text-white/90" : "text-[13px] font-medium text-ink dark:text-white/90"}>
              {stage.title}
            </p>
            <p
              className={
                dark
                  ? "mt-1 text-[11px] leading-relaxed text-white/62"
                  : "mt-1 text-[11px] leading-relaxed text-ink/68 dark:text-white/62"
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
                  : "relative hidden h-px w-8 shrink-0 bg-accent/20 dark:bg-white/10 sm:block"
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

import type { ReactNode } from "react";

/** A small fake app-window frame (traffic-light dots + a label) wrapping
 * an abstract, illustrative mockup of a real feature — used by the
 * homepage's "How it works" cards (InputScreen.tsx).
 *
 * Deliberately NOT a real screenshot and never claims to be one: content
 * inside is bars/pills/icons, not actual product pixels or invented
 * lyrics. That's what keeps these honest after the /compare page was
 * removed for over-representing on real example - a stylized diagram of
 * a real mechanism (repetition preserved, a change logged with a reason,
 * a language pair) makes a narrower, verifiable claim than a screenshot
 * would, without needing a real benchmark run in every language to back
 * it up. The traffic-light dots reuse the pattern the old showcase card
 * used for the same "this is a window, not a claim" framing. */
export function MockWindow({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="overflow-hidden rounded-xl border border-white/10 bg-black/30">
      <div className="flex items-center gap-1.5 border-b border-white/10 px-3 py-2">
        <span className="h-2 w-2 rounded-full bg-white/15" />
        <span className="h-2 w-2 rounded-full bg-white/15" />
        <span className="h-2 w-2 rounded-full bg-white/15" />
        <span className="ml-2 truncate text-[10px] text-white/45">{label}</span>
      </div>
      <div className="p-4">{children}</div>
    </div>
  );
}

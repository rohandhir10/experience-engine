"use client";

import { useState } from "react";
import type { DeviationFragment } from "@/lib/types";
import { splitByDeviations } from "@/lib/deviationHighlight";

// Renders the shipped CASTIA line with a dotted underline on each phrase the
// Burden-of-Change ledger names, and a click-to-toggle tooltip showing the
// literal wording it replaced. The tooltip reuses the section's own `why`
// sentence for its prose - never `deviation.justification` directly, which
// is written for an engineer auditing a ruling, not a listener (see
// server/mapping.py::_deviations_payload).
export function DeviationText({
  text,
  deviations,
  why,
}: {
  text: string;
  deviations?: DeviationFragment[];
  why: string;
}) {
  const [openIndex, setOpenIndex] = useState<number | null>(null);
  const segments = splitByDeviations(text, deviations);

  let deviationIndex = -1;

  return (
    <span className="whitespace-pre-line">
      {segments.map((segment, i) => {
        if (segment.type === "text") {
          return <span key={i}>{segment.text}</span>;
        }
        deviationIndex += 1;
        const thisIndex = deviationIndex;
        const isOpen = openIndex === thisIndex;
        return (
          <span key={i} className="relative">
            <span
              role="button"
              tabIndex={0}
              onClick={() => setOpenIndex(isOpen ? null : thisIndex)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  setOpenIndex(isOpen ? null : thisIndex);
                }
              }}
              className="cursor-pointer underline decoration-dotted decoration-accent/50 underline-offset-4 transition hover:decoration-accent"
            >
              {segment.text}
            </span>
            {isOpen && (
              <span
                role="tooltip"
                className="absolute left-1/2 top-full z-10 mt-2 w-64 -translate-x-1/2 rounded-xl border border-black/[0.08] bg-paper px-4 py-3 text-left text-[13px] font-sans not-italic leading-relaxed text-ink shadow-lg dark:border-white/[0.08] dark:bg-paper-dark dark:text-ink-dark"
              >
                <span className="block text-[10px] font-medium uppercase tracking-[0.1em] text-ink/40 dark:text-ink-dark/40">
                  Literal
                </span>
                <span className="mt-1 block text-ink/70 dark:text-ink-dark/70">
                  {segment.deviation.fragmentOriginal}
                </span>
                <span className="mt-3 block text-ink/60 dark:text-ink-dark/60">{why}</span>
              </span>
            )}
          </span>
        );
      })}
    </span>
  );
}

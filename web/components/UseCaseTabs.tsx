"use client";

import { useState } from "react";

const TABS: { label: string; caption: string }[] = [
  {
    label: "Fans",
    caption:
      "Streaming put music from everywhere in front of everyone. A literal translation usually kills the reason a song moved you — this keeps the reason intact.",
  },
  {
    label: "Singers & covers",
    caption:
      "A singable adaptation needs to scan and breathe like a real lyric, not read like a subtitle. Start from something built for performance, not a word-for-word draft.",
  },
  {
    label: "Language learners",
    caption:
      "Every real change comes with a plain-language reason — what the line actually says, what changed, and why, instead of a translation you have to take on faith.",
  },
];

/** The one small interactive piece on this page — three labeled tabs
 * switching a caption under the shared real screenshot below
 * (comparison-card.png). Deliberately does NOT swap the image per tab:
 * there is exactly one real captured example (see scripts/capture-
 * screenshots.mjs), and pretending each audience gets its own visual
 * would be the same single-example-standing-in-for-everything problem
 * the rest of this homepage pass exists to avoid. What's honest to
 * switch is who a real feature is useful for — that claim doesn't
 * depend on which screenshot illustrates it. */
export function UseCaseTabs() {
  const [active, setActive] = useState(0);

  return (
    <div>
      <div className="flex flex-wrap gap-2">
        {TABS.map((tab, i) => (
          <button
            key={tab.label}
            type="button"
            onClick={() => setActive(i)}
            className={`rounded-full border px-3 py-1.5 text-[13px] transition ${
              active === i
                ? "border-accent/40 bg-accent/10 text-accent"
                : "border-black/10 text-ink/68 hover:text-ink/80 dark:border-white/10 dark:text-ink-dark/68 dark:hover:text-ink-dark/80"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <p className="mt-4 max-w-md text-[14px] leading-relaxed text-ink/78 dark:text-ink-dark/78">
        {TABS[active].caption}
      </p>
    </div>
  );
}

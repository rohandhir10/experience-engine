"use client";

import { useState } from "react";
import Link from "next/link";
import type { ExperienceResult } from "@/lib/types";
import { SiteHeader } from "./SiteHeader";
import { ComparisonCard } from "./ComparisonCard";
import { CopyLinkButton } from "./CopyLinkButton";

export function ResultScreen({ result }: { result: ExperienceResult }) {
  const [showOriginal, setShowOriginal] = useState(false);
  const originalById = Object.fromEntries(
    result.original.map((o) => [o.id, o.text])
  );

  return (
    <main className="min-h-screen px-6 pb-28 pt-8 sm:px-10">
      <SiteHeader
        right={
          <>
            <button
              role="switch"
              aria-checked={showOriginal}
              aria-label="Show original script"
              onClick={() => setShowOriginal((v) => !v)}
              className="flex items-center gap-2 rounded-full text-[13px] text-ink/45 transition hover:text-ink/70 dark:text-ink-dark/45 dark:hover:text-ink-dark/70"
            >
              <span
                aria-hidden
                className={`relative h-[18px] w-[32px] rounded-full transition-colors duration-200 ${
                  showOriginal ? "bg-accent" : "bg-black/10 dark:bg-white/15"
                }`}
              >
                {/* Always a light knob with a shadow, in both themes — it
                    needs to read against its own track's color, not match
                    the page background, or it vanishes in dark mode. */}
                <span
                  className={`absolute top-[2px] h-[14px] w-[14px] rounded-full bg-white shadow-[0_1px_3px_rgba(0,0,0,0.4)] transition-transform duration-200 ${
                    showOriginal ? "translate-x-[16px]" : "translate-x-[2px]"
                  }`}
                />
              </span>
              <span>Original</span>
            </button>

            <CopyLinkButton resultId={result.id} />

            <Link
              href="/"
              className="text-[13px] text-ink/45 transition hover:text-ink/70 dark:text-ink-dark/45 dark:hover:text-ink-dark/70"
            >
              ← Start over
            </Link>
          </>
        }
      />

      <div className="animate-fade-up mx-auto mt-16 max-w-2xl text-center sm:mt-24">
        <p className="font-serif text-[1.7rem] leading-[1.4] tracking-tight text-ink dark:text-ink-dark sm:text-[2.05rem]">
          {result.hook}
        </p>
      </div>

      <div className="mx-auto mt-20 flex max-w-2xl flex-col gap-6 sm:mt-24">
        {result.sections.map((section, i) => (
          <ComparisonCard
            key={section.id}
            section={section}
            index={i}
            original={originalById[section.id]}
            showOriginal={showOriginal}
          />
        ))}
      </div>
    </main>
  );
}

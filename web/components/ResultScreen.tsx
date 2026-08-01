"use client";

import { useState } from "react";
import type { ExperienceResult } from "@/lib/types";
import { Logo } from "./Logo";
import { ComparisonCard } from "./ComparisonCard";

export function ResultScreen({
  result,
  onReset,
}: {
  result: ExperienceResult;
  onReset: () => void;
}) {
  const [showOriginal, setShowOriginal] = useState(false);
  const originalById = Object.fromEntries(
    result.original.map((o) => [o.id, o.text])
  );

  return (
    <main className="min-h-screen px-6 pb-28 pt-8 sm:px-10">
      <div className="mx-auto flex max-w-3xl items-center justify-between border-b border-black/[0.05] pb-5 dark:border-white/[0.05]">
        <Logo />
        <div className="flex items-center gap-6">
          <button
            onClick={() => setShowOriginal((v) => !v)}
            className="flex items-center gap-2 rounded-full text-[13px] text-ink/45 transition hover:text-ink/70 dark:text-ink-dark/45 dark:hover:text-ink-dark/70"
          >
            <span
              className={`relative h-[18px] w-[32px] rounded-full transition-colors duration-200 ${
                showOriginal
                  ? "bg-accent"
                  : "bg-black/10 dark:bg-white/10"
              }`}
            >
              <span
                className={`absolute top-[2px] h-[14px] w-[14px] rounded-full bg-white shadow-sm transition-transform duration-200 dark:bg-paper-dark ${
                  showOriginal ? "translate-x-[16px]" : "translate-x-[2px]"
                }`}
              />
            </span>
            Original script
          </button>
          <button
            onClick={onReset}
            className="text-[13px] text-ink/45 transition hover:text-ink/70 dark:text-ink-dark/45 dark:hover:text-ink-dark/70"
          >
            ← Start over
          </button>
        </div>
      </div>

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

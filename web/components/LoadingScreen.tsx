"use client";

import { useEffect, useState } from "react";
import { Logo } from "./Logo";

// Shown ONLY when the caller has no real progress yet to report (before
// the first poll response lands, or on a page - the share pages, the
// dashboard - that isn't tracking a job at all). These messages are
// scripted, not measured against real backend progress - the point
// isn't literal accuracy, it's making the wait feel like it's doing
// something specific instead of nothing. The last message holds
// indefinitely if the real call runs long. Once real `progress` is
// passed in, it replaces these outright - real status beats a guess.
const STATUSES = [
  "Understanding the song…",
  "Finding what gets lost in translation…",
  "Preserving the writer's voice…",
  "Almost there…",
];

const STEP_MS = 3200;

export function LoadingScreen({
  progress,
}: {
  // lib/useAdaptSubmit.ts's SongAdaptProgress - only its `message` is
  // shown (the count is already folded into that text server-side, e.g.
  // "Section 2/5: adapting…" - server/main.py::_run_adaptation). Omit
  // entirely for a caller with no job to report against.
  progress?: { message: string } | null;
} = {}) {
  const [step, setStep] = useState(0);

  useEffect(() => {
    if (progress) return; // real status is in - stop cycling the guesses.
    if (step >= STATUSES.length - 1) return;
    const timer = setTimeout(() => setStep((s) => s + 1), STEP_MS);
    return () => clearTimeout(timer);
  }, [step, progress]);

  const message = progress?.message ?? STATUSES[step];

  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-6">
      <div className="fixed left-6 top-6 sm:left-10 sm:top-10">
        <Logo />
      </div>

      <div
        className="flex flex-col items-center gap-6 text-center"
        role="status"
        aria-live="polite"
      >
        <span className="h-5 w-5 animate-spin rounded-full border-[1.5px] border-ink/15 border-t-ink/60 dark:border-ink-dark/15 dark:border-t-ink-dark/60" />
        <p
          key={message}
          className="animate-fade-up font-serif text-[1.35rem] text-ink/78 dark:text-ink-dark/78"
        >
          {message}
        </p>
        {!progress && (
          <div className="flex items-center gap-1.5" aria-hidden>
            {STATUSES.map((_, i) => (
              <span
                key={i}
                className={`h-1 w-1 rounded-full transition-colors duration-300 ${
                  i <= step
                    ? "bg-ink/50 dark:bg-ink-dark/50"
                    : "bg-ink/15 dark:bg-ink-dark/15"
                }`}
              />
            ))}
          </div>
        )}
      </div>
    </main>
  );
}

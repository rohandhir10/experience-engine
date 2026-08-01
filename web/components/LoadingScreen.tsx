"use client";

import { useEffect, useState } from "react";
import { Logo } from "./Logo";

// A real engine run takes anywhere from a few seconds to closer to a
// minute, depending on how many sections a song has and whether the Judge
// calls in specialists. These messages are scripted, not measured against
// real backend progress - the point isn't literal accuracy, it's making
// the wait feel like it's doing something specific instead of nothing.
// The last message holds indefinitely if the real call runs long.
const STATUSES = [
  "Understanding the song…",
  "Finding what gets lost in translation…",
  "Preserving the writer's voice…",
  "Almost there…",
];

const STEP_MS = 3200;

export function LoadingScreen() {
  const [step, setStep] = useState(0);

  useEffect(() => {
    if (step >= STATUSES.length - 1) return;
    const timer = setTimeout(() => setStep((s) => s + 1), STEP_MS);
    return () => clearTimeout(timer);
  }, [step]);

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
          key={step}
          className="animate-fade-up font-serif text-[1.35rem] text-ink/70 dark:text-ink-dark/70"
        >
          {STATUSES[step]}
        </p>
      </div>
    </main>
  );
}

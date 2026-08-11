"use client";

import { useMemo, useRef, useState } from "react";
import Link from "next/link";
import type { ExperienceResult } from "@/lib/types";
import { SiteHeader } from "./SiteHeader";
import { ComparisonCard } from "./ComparisonCard";
import { CopyLinkButton } from "./CopyLinkButton";
import { SaveControls } from "./SaveControls";
import { YoutubeSyncPlayer } from "./YoutubeSyncPlayer";

export function ResultScreen({ result }: { result: ExperienceResult }) {
  const [showOriginal, setShowOriginal] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const cardRefs = useRef<(HTMLDivElement | null)[]>([]);
  const originalById = Object.fromEntries(
    result.original.map((o) => [o.id, o.text])
  );

  // Only sections that survived review with their timing intact carry
  // startSeconds/endSeconds (server/main.py drops all of it on a section-
  // count mismatch) - undefined for every result that didn't come from a
  // YouTube draft at all, which is most of them.
  const activeIndex = useMemo(() => {
    if (!result.videoId) return null;
    const index = result.sections.findIndex(
      (s) =>
        s.startSeconds !== undefined &&
        s.endSeconds !== undefined &&
        currentTime >= s.startSeconds &&
        currentTime < s.endSeconds
    );
    return index >= 0 ? index : null;
  }, [currentTime, result.sections, result.videoId]);

  function handleTimeUpdate(seconds: number) {
    setCurrentTime((prev) => {
      // Avoid a state update (and the re-render it triggers) on every
      // 400ms poll when playback hasn't meaningfully moved - paused video,
      // or between polls that land within the same second.
      if (Math.abs(seconds - prev) < 0.5) return prev;
      const el = cardRefs.current[
        result.sections.findIndex(
          (s) =>
            s.startSeconds !== undefined &&
            s.endSeconds !== undefined &&
            seconds >= s.startSeconds &&
            seconds < s.endSeconds
        )
      ];
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "center" });
      }
      return seconds;
    });
  }

  return (
    <main className="min-h-screen px-6 pb-28 pt-8 sm:px-10">
      {/* result.id === "demo" is the one fully-captured production run in
          the whole project (lib/demo-data.ts) - a real Hindi romantic
          ballad, not a fabricated one, but also not representative of
          any particular genre, mood, or language this tool is "for."
          Shown without this note, a visitor who isn't into that kind of
          song reasonably reads it as a taste/culture statement rather
          than what it actually is: one illustration of the mechanism
          (literal reading -> adapted line -> why it changed), which
          applies the same way regardless of which song demonstrates it. */}
      {result.id === "demo" && (
        <div className="mx-auto mb-8 max-w-2xl rounded-xl border border-black/[0.10] bg-black/[0.02] px-4 py-3 text-center text-[13px] leading-relaxed text-ink/50 dark:border-white/[0.10] dark:bg-white/[0.02] dark:text-ink-dark/50">
          One real example, showing how the engine works — not a preview
          of what genre or language your own song needs to be.{" "}
          <Link
            href="/music#lyrics"
            className="underline decoration-ink/20 underline-offset-4 hover:text-ink/80 dark:decoration-ink-dark/20 dark:hover:text-ink-dark/80"
          >
            Try any song →
          </Link>
        </div>
      )}
      <SiteHeader
        minimal
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

            {/* Renders nothing when signed out — see SaveControls. The
                demo result isn't a real cached adaptation (lib/demo-data.ts),
                so it can't be saved: showing a star that always fails and
                flips back would be worse than showing none. */}
            {result.id !== "demo" && <SaveControls resultId={result.id} />}

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
        {result.phonemeRepetitionSimilarity != null && (
          <p className="mt-5 text-[12px] leading-relaxed text-ink/35 dark:text-ink-dark/35">
            Repetition pattern:{" "}
            {result.phonemeRepetitionSimilarity >= 0
              ? "follows a literal reading of the lyrics, section by section"
              : "runs opposite a literal reading of the lyrics, section by section"}{" "}
            ({result.phonemeRepetitionSimilarity >= 0 ? "+" : ""}
            {result.phonemeRepetitionSimilarity.toFixed(2)})
          </p>
        )}
      </div>

      {result.videoId && (
        <div className="animate-fade-up mx-auto mt-14 max-w-2xl">
          <YoutubeSyncPlayer videoId={result.videoId} onTimeUpdate={handleTimeUpdate} />
          <p className="mt-3 text-center text-[12px] text-ink/35 dark:text-ink-dark/35">
            The highlighted section below follows the video as it plays.
          </p>
        </div>
      )}

      <div className="mx-auto mt-20 flex max-w-2xl flex-col gap-6 sm:mt-24">
        {result.sections.map((section, i) => (
          <ComparisonCard
            key={section.id}
            ref={(el) => {
              cardRefs.current[i] = el;
            }}
            section={section}
            index={i}
            original={originalById[section.id]}
            showOriginal={showOriginal}
            active={i === activeIndex}
            poeticRegister={i === 0 ? result.poeticRegister : undefined}
          />
        ))}
      </div>
    </main>
  );
}

"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { MockWindow } from "./MockWindow";
import { SiteHeader } from "./SiteHeader";
import { TargetLanguageSelect } from "./TargetLanguageSelect";
import { YoutubeImportField, type YoutubeDraft } from "./YoutubeImportField";
import { detectSourceLanguage } from "@/lib/detectLanguage";
import { LANGUAGES, sourceHintFor } from "@/lib/languages";
import type { YoutubeSource } from "@/lib/useAdaptSubmit";

const MIN_ROWS = 6;
const MAX_TEXTAREA_HEIGHT_PX = 380;

// Mirrors engine/text_ingest.py's split_into_sections exactly - used only
// to notice when an edit has changed the section *count* a YouTube draft
// came with, so its per-section timing (positional, not content-matched)
// gets dropped rather than silently synced to the wrong lines.
function countBlocks(text: string): number {
  return text
    .trim()
    .split(/\n\s*\n+/)
    .map((b) => b.trim())
    .filter(Boolean).length;
}

export function InputScreen({
  onSubmit,
  loading,
  error,
}: {
  onSubmit: (
    text: string,
    targetLanguage: string,
    sourceLanguage?: string,
    youtube?: YoutubeSource
  ) => void;
  loading: boolean;
  error: string | null;
}) {
  const [text, setText] = useState("");
  const [targetLanguage, setTargetLanguage] = useState("English");
  // Only meaningful (and only shown) once a non-English target is picked —
  // server/main.py requires an explicit source_language for every
  // direction except "any supported language -> English", the one case
  // auto-detect has actually been tested against.
  const [sourceLanguage, setSourceLanguage] = useState("English");
  // Once the user has explicitly picked a "From" language themselves,
  // auto-detection stops overwriting it — a wrong guess should cost one
  // click, not a fight with the box every time they type.
  const [sourceLanguageTouched, setSourceLanguageTouched] = useState(false);
  const [mode, setMode] = useState<"paste" | "youtube">("paste");
  const [youtubeDraft, setYoutubeDraft] = useState<YoutubeDraft | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  function submit() {
    if (!text.trim() || loading) return;
    const youtube: YoutubeSource | undefined = youtubeDraft
      ? { videoId: youtubeDraft.videoId, sectionTimings: youtubeDraft.sections }
      : undefined;
    onSubmit(
      text,
      targetLanguage,
      targetLanguage === "English" ? undefined : sourceLanguage,
      youtube
    );
  }

  function handleImported(draft: YoutubeDraft) {
    setYoutubeDraft(draft);
    setText(draft.draftText);
    if (!sourceLanguageTouched) {
      const detected = detectSourceLanguage(draft.draftText);
      if (detected && detected !== targetLanguage) {
        setSourceLanguage(detected);
      }
    }
    // A textarea that wasn't yet mounted/measured can't auto-grow from a
    // ref call made before React commits the new value - next tick is
    // enough for that paint to have happened.
    setTimeout(() => {
      if (textareaRef.current) autoGrow(textareaRef.current);
    }, 0);
  }

  function autoGrow(el: HTMLTextAreaElement) {
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, MAX_TEXTAREA_HEIGHT_PX)}px`;
  }

  return (
    <main className="min-h-screen bg-[#0b0b0c] px-6 pb-28 pt-8 sm:px-10">
      {/* A dark, always-on-brand shell (not theme-reactive) so the product
          reads the same regardless of system light/dark mode — matching
          the reference design. Sign In / Get Started live in the nav, same
          as every page, but there's no pricing table or feature grid
          competing with the input itself. Fixed top margin below, not
          flex-1-centered — same convention as every other page
          (dashboard/pricing/sign-in all use a fixed mt-*), so the gap
          before the showcase card stays consistent instead of stretching
          or shrinking with viewport height. */}
      <SiteHeader active="home" forceDark />

      <div className="mx-auto flex w-full max-w-2xl flex-col items-center pt-16 text-center sm:pt-20">
        <h1 className="animate-fade-up text-[2.3rem] font-semibold leading-[1.1] tracking-tight text-white sm:text-[2.9rem]">
          Adapt the feeling.
          <br />
          Not just the words.
        </h1>
        <p
          className="animate-fade-up mt-4 text-[14px] text-white/40"
          style={{ animationDelay: "80ms" }}
        >
          {sourceHintFor(targetLanguage, sourceLanguage)}
        </p>

        <div
          className="animate-fade-up mt-5 flex flex-col items-center gap-4"
          style={{ animationDelay: "120ms" }}
        >
          <div className="flex flex-wrap items-center justify-center gap-3">
            {targetLanguage !== "English" && (
              <TargetLanguageSelect
                label="From"
                value={sourceLanguage}
                onChange={(next) => {
                  setSourceLanguage(next);
                  setSourceLanguageTouched(true);
                }}
                options={LANGUAGES.filter((lang) => lang !== targetLanguage)}
                dark
              />
            )}
            <TargetLanguageSelect
              label="Adapt into"
              value={targetLanguage}
              onChange={(next) => {
                setTargetLanguage(next);
                if (next === sourceLanguage) {
                  // Source and target can't match - fall back to
                  // whichever of the roster isn't the new target.
                  setSourceLanguage(LANGUAGES.find((lang) => lang !== next) ?? "English");
                }
              }}
              dark
            />
          </div>

          <div className="flex items-center gap-1 rounded-full border border-white/10 p-1 text-[13px]">
            <button
              type="button"
              onClick={() => setMode("paste")}
              className={`rounded-full px-4 py-1.5 transition ${
                mode === "paste" ? "bg-white text-black" : "text-white/50 hover:text-white/80"
              }`}
            >
              Paste lyrics
            </button>
            <button
              type="button"
              onClick={() => setMode("youtube")}
              className={`rounded-full px-4 py-1.5 transition ${
                mode === "youtube" ? "bg-white text-black" : "text-white/50 hover:text-white/80"
              }`}
            >
              From YouTube
            </button>
          </div>

          {mode === "youtube" && (
            <div className="w-full max-w-md">
              <YoutubeImportField dark onImported={handleImported} />
              {youtubeDraft && (
                <p className="mt-3 text-[12px] leading-relaxed text-white/35">
                  {youtubeDraft.warning} Review the text below before adapting it.
                </p>
              )}
            </div>
          )}
        </div>

        <form
          className="animate-fade-up mt-9 w-full"
          style={{ animationDelay: "160ms" }}
          onSubmit={(e) => {
            e.preventDefault();
            submit();
          }}
        >
          <label htmlFor="lyrics" className="sr-only">
            Paste song lyrics
          </label>
          <textarea
            ref={textareaRef}
            id="lyrics"
            value={text}
            onChange={(e) => {
              setText(e.target.value);
              autoGrow(e.target);
              if (youtubeDraft && countBlocks(e.target.value) !== youtubeDraft.sections.length) {
                // The edit changed how many sections this splits into -
                // the draft's positional timing no longer means anything,
                // so drop it rather than sync to the wrong lyric line.
                setYoutubeDraft(null);
              }
              if (!sourceLanguageTouched) {
                const detected = detectSourceLanguage(e.target.value);
                if (detected && detected !== targetLanguage) {
                  setSourceLanguage(detected);
                }
              }
            }}
            onKeyDown={(e) => {
              if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
                e.preventDefault();
                submit();
              }
            }}
            placeholder="Paste song lyrics…"
            rows={MIN_ROWS}
            autoFocus
            aria-describedby={error ? "lyrics-error" : undefined}
            className="w-full resize-none overflow-y-auto rounded-2xl border border-white/10 bg-white/[0.04] px-6 py-5 text-[15px] leading-relaxed text-white placeholder:text-white/25 transition focus:border-white/20"
          />

          {error && (
            <p id="lyrics-error" role="alert" className="mt-3 text-[13px] text-red-400/80">
              {error}
            </p>
          )}

          <div className="mt-6 flex items-center justify-center gap-4">
            <button
              type="submit"
              disabled={!text.trim() || loading}
              className="inline-flex items-center justify-center gap-2 rounded-full bg-white px-8 py-3 text-[14px] font-medium text-black transition active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-30"
            >
              {loading && (
                <span className="h-3 w-3 animate-spin rounded-full border-[1.5px] border-black/30 border-t-black" />
              )}
              {loading ? "Listening" : "Adapt Song"}
            </button>

            {text.trim() && !loading && (
              <span className="animate-fade-up text-[12px] text-white/25">⌘ + Enter</span>
            )}
          </div>
        </form>

        {/* "See how it works," not "see an example" - the one real demo
            available (lib/demo-data.ts) is a specific romantic Bollywood
            ballad, since it's the only fully-captured production run in
            the project. Framing it as THE example implies that's the
            kind of song this is for; framing it as a mechanism demo
            (literal vs. adapted vs. why, for one song, in one language)
            is honest regardless of which song happens to illustrate it -
            see the banner on the demo page itself for the same reasoning. */}
        <Link
          href="/s/demo"
          className="animate-fade-up mt-8 text-[13px] text-white/35 underline decoration-white/15 underline-offset-4 transition hover:text-white/60 hover:decoration-white/30"
          style={{ animationDelay: "220ms" }}
        >
          See how it works
        </Link>
      </div>

      {/* A language matrix, not a single lyric — AURA supports six
          languages in any direction, and the only real, fully-benchmarked
          comparison example ever generated (see benchmark/README.md)
          happens to be one Hindi/Punjabi song. Showing that one example
          prominently and unprompted on the homepage read as "built for
          Hindi songs," which is the opposite of what this tool is. This
          states the actual language coverage instead of implying it from
          a single sample - no /compare page to link to anymore (see
          the Use Cases section below for why). */}
      <div
        className="animate-fade-up mx-auto mt-16 w-full max-w-2xl text-center"
        style={{ animationDelay: "260ms" }}
      >
        <p className="text-[12px] uppercase tracking-[0.15em] text-white/25">
          Six languages, one engine
        </p>
        <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
          {LANGUAGES.map((lang) => (
            <span
              key={lang}
              className="rounded-full border border-white/10 px-3 py-1 text-[13px] text-white/50"
            >
              {lang}
            </span>
          ))}
        </div>
      </div>

      {/* "How it works," replacing the old /compare page entirely. That
          page's only content was one real Hindi song shown against Google
          Translate/a single GPT prompt — informative, but it was also the
          site's one piece of "proof," and pairing a features section with
          it would have re-created the exact single-example problem this
          whole pass exists to fix (one language standing in for the whole
          product). Each card below is a stylized diagram of one real
          mechanism (MockWindow.tsx) — never a screenshot, never invented
          lyrics — which makes a narrower, easier-to-stand-behind claim
          than a demo does: "here is how this specific thing works,"
          true regardless of which language or genre someone actually
          brings to it. The real benchmark tooling (benchmark/cli.py)
          still exists for internal quality checks; it just isn't a
          public page anymore. Asymmetric grid (not a uniform card grid)
          deliberately, on a direct visual note from a Framer-style
          reference layout - varied card widths read as designed, a
          repeated identical box reads as a generated template. */}
      <div
        id="features"
        className="animate-fade-up mx-auto mt-24 w-full max-w-4xl scroll-mt-20"
        style={{ animationDelay: "280ms" }}
      >
        <p className="text-[12px] uppercase tracking-[0.15em] text-white/25">How it works</p>
        <h2 className="mt-3 max-w-lg font-serif text-[1.7rem] leading-[1.25] text-white sm:text-[2rem]">
          Not translation.
          <br />A rewrite that still means it.
        </h2>

        <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-6">
          <FeatureCard
            span="sm:col-span-4"
            title="Every real change, logged with a reason"
            description="A literal reading sits next to the adapted line. Nothing shifts without a specific, checkable reason attached to it."
          >
            <div className="grid grid-cols-2 gap-4">
              <div>
                <span className="text-[9px] uppercase tracking-wide text-white/25">Literal</span>
                <div className="mt-2 space-y-1.5">
                  <div className="h-1.5 w-full rounded-full bg-white/10" />
                  <div className="h-1.5 w-4/5 rounded-full bg-white/10" />
                  <div className="h-1.5 w-3/5 rounded-full bg-white/10" />
                </div>
              </div>
              <div>
                <span className="text-[9px] uppercase tracking-wide text-accent">Aura</span>
                <div className="mt-2 space-y-1.5">
                  <div className="h-1.5 w-5/6 rounded-full bg-accent/50" />
                  <div className="h-1.5 w-2/3 rounded-full bg-accent/50" />
                  <div className="h-1.5 w-1/2 rounded-full bg-accent/50" />
                </div>
              </div>
            </div>
            <div className="mt-4 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-[11px] leading-relaxed text-white/40">
              <span className="text-white/60">Why:</span> the line repeats three times in
              the source — it repeats three times here too.
            </div>
          </FeatureCard>

          <FeatureCard
            span="sm:col-span-2"
            title="Any language, either direction"
            description="Six languages, any pairing — not a fixed source and a fixed target."
          >
            <div className="flex flex-col gap-2">
              {[
                ["Hindi", "Spanish"],
                ["Korean", "English"],
                ["Japanese", "Urdu"],
              ].map(([from, to]) => (
                <div
                  key={`${from}-${to}`}
                  className="flex items-center gap-1.5 text-[11px] text-white/50"
                >
                  <span className="rounded-full border border-white/10 px-2 py-0.5">{from}</span>
                  <span className="text-white/20">→</span>
                  <span className="rounded-full border border-accent/40 px-2 py-0.5 text-accent">
                    {to}
                  </span>
                </div>
              ))}
            </div>
          </FeatureCard>

          <FeatureCard
            span="sm:col-span-3"
            title="Imports straight from YouTube"
            description="Paste a link — captions become reviewable sections, no manual retyping."
          >
            <div className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2">
              <svg viewBox="0 0 24 24" className="h-3.5 w-3.5 shrink-0 fill-white/30">
                <path d="M8 5.5v13l11-6.5z" />
              </svg>
              <span className="truncate text-[11px] text-white/35">youtube.com/watch?v=…</span>
            </div>
            <p className="mt-3 text-[11px] leading-relaxed text-white/30">
              Reviewed before anything runs — never piped straight into the engine.
            </p>
          </FeatureCard>

          <FeatureCard
            span="sm:col-span-3"
            title="Keep what you find"
            description="Star a result or file it into a collection — it's there next time, not lost in a chat history."
          >
            <div className="flex items-center gap-3">
              <svg
                viewBox="0 0 24 24"
                className="h-4 w-4 shrink-0 fill-accent"
                aria-hidden="true"
              >
                <path d="M12 3.5l2.6 5.3 5.9.85-4.25 4.15 1 5.85L12 16.9l-5.25 2.75 1-5.85L3.5 9.65l5.9-.85z" />
              </svg>
              <div className="flex flex-wrap gap-1.5">
                <span className="rounded-full border border-white/10 px-2 py-0.5 text-[11px] text-white/40">
                  Hindi Rock
                </span>
                <span className="rounded-full border border-white/10 px-2 py-0.5 text-[11px] text-white/40">
                  Covers
                </span>
              </div>
            </div>
          </FeatureCard>
        </div>
      </div>
    </main>
  );
}

function FeatureCard({
  span,
  title,
  description,
  children,
}: {
  span: string;
  title: string;
  description: string;
  children: React.ReactNode;
}) {
  return (
    <div className={`${span} flex flex-col`}>
      <MockWindow label={title}>{children}</MockWindow>
      <h3 className="mt-4 text-[14px] font-medium text-white/85">{title}</h3>
      <p className="mt-1.5 text-[13px] leading-relaxed text-white/40">{description}</p>
    </div>
  );
}

"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { SiteHeader } from "./SiteHeader";
import { TargetLanguageSelect } from "./TargetLanguageSelect";
import { YoutubeImportField, type YoutubeDraft } from "./YoutubeImportField";
import { comparisonEntries } from "@/lib/comparison-data";
import { sourceHintFor } from "@/lib/languages";
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
  onSubmit: (text: string, targetLanguage: string, youtube?: YoutubeSource) => void;
  loading: boolean;
  error: string | null;
}) {
  const [text, setText] = useState("");
  const [targetLanguage, setTargetLanguage] = useState("English");
  const [mode, setMode] = useState<"paste" | "youtube">("paste");
  const [youtubeDraft, setYoutubeDraft] = useState<YoutubeDraft | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  function submit() {
    if (!text.trim() || loading) return;
    const youtube: YoutubeSource | undefined = youtubeDraft
      ? { videoId: youtubeDraft.videoId, sectionTimings: youtubeDraft.sections }
      : undefined;
    onSubmit(text, targetLanguage, youtube);
  }

  function handleImported(draft: YoutubeDraft) {
    setYoutubeDraft(draft);
    setText(draft.draftText);
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

  const featured = comparisonEntries[0];
  const featuredAura = featured?.sections[0]?.systems.aura;
  const featuredSource = featured?.sections[0]?.source;

  return (
    <main className="flex min-h-screen flex-col bg-[#0b0b0c] px-6 pb-20 pt-8 sm:px-10">
      {/* A dark, always-on-brand shell (not theme-reactive) so the product
          reads the same regardless of system light/dark mode — matching
          the reference design. Sign In / Get Started live in the nav, same
          as every page, but there's no pricing table or feature grid
          competing with the input itself. */}
      <SiteHeader active="home" forceDark />

      <div className="mx-auto flex w-full max-w-2xl flex-1 flex-col items-center justify-center text-center">
        <h1 className="animate-fade-up text-[2.3rem] font-semibold leading-[1.1] tracking-tight text-white sm:text-[2.9rem]">
          Adapt the feeling.
          <br />
          Not just the words.
        </h1>
        <p
          className="animate-fade-up mt-4 text-[14px] text-white/40"
          style={{ animationDelay: "80ms" }}
        >
          {sourceHintFor(targetLanguage)}
        </p>

        <div
          className="animate-fade-up mt-5 flex flex-col items-center gap-4"
          style={{ animationDelay: "120ms" }}
        >
          <TargetLanguageSelect value={targetLanguage} onChange={setTargetLanguage} dark />

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

        <Link
          href="/s/demo"
          className="animate-fade-up mt-8 text-[13px] text-white/35 underline decoration-white/15 underline-offset-4 transition hover:text-white/60 hover:decoration-white/30"
          style={{ animationDelay: "220ms" }}
        >
          See an example first
        </Link>
      </div>

      {featured && featuredAura && (
        <div className="animate-fade-up mx-auto mt-16 w-full max-w-3xl" style={{ animationDelay: "260ms" }}>
          <div className="overflow-hidden rounded-2xl border border-white/10 bg-white/[0.02]">
            <div className="flex items-center gap-2 border-b border-white/10 px-5 py-3">
              <span className="h-2.5 w-2.5 rounded-full bg-white/15" />
              <span className="h-2.5 w-2.5 rounded-full bg-white/15" />
              <span className="h-2.5 w-2.5 rounded-full bg-white/15" />
              <span className="ml-3 text-[12px] text-white/35">
                {featured.title} — real production run
              </span>
            </div>
            <div className="grid gap-6 px-6 py-7 sm:grid-cols-2 sm:px-8">
              <div>
                <p className="text-[11px] font-medium uppercase tracking-[0.15em] text-white/30">
                  Original
                </p>
                <p className="mt-3 whitespace-pre-line text-[14px] leading-relaxed text-white/40">
                  {featuredSource}
                </p>
              </div>
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.15em] text-accent">
                  AURA
                </p>
                <p className="mt-3 whitespace-pre-line text-[16px] leading-relaxed text-white">
                  {featuredAura}
                </p>
              </div>
            </div>
            <div className="border-t border-white/10 px-6 py-3 text-right sm:px-8">
              <Link href="/compare" className="text-[13px] text-white/45 transition hover:text-white/75">
                See the full comparison, unedited →
              </Link>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}

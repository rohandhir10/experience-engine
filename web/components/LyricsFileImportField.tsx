"use client";

import { useRef, useState } from "react";
import { buildDraftFromFile, LyricsImportError } from "@/lib/lyricsImport";
import type { YoutubeDraft } from "./YoutubeImportField";

/** Drag-and-drop / file-picker entry point for .lrc and .srt files -
 * parsed entirely client-side (lib/lyricsImport.ts), no network round
 * trip, unlike YoutubeImportField's fetch. Hands back the same
 * `YoutubeDraft` shape (videoId omitted - there's no video here) so
 * InputScreen.tsx's existing handleImported/review/submit flow needs no
 * branching on where the timing came from. */
export function LyricsFileImportField({
  onImported,
  dark = false,
}: {
  onImported: (draft: YoutubeDraft) => void;
  dark?: boolean;
}) {
  const [error, setError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleFile(file: File) {
    setError(null);
    if (!/\.(lrc|srt)$/i.test(file.name)) {
      setError("Only .lrc or .srt files are supported here.");
      return;
    }
    try {
      const text = await file.text();
      const draft = buildDraftFromFile(file.name, text);
      onImported(draft);
    } catch (err) {
      setError(
        err instanceof LyricsImportError
          ? err.message
          : `Could not read ${file.name}.`
      );
    }
  }

  const fieldClass = dark
    ? "border-white/10 hover:border-white/20"
    : "border-black/[0.12] hover:border-black/20 dark:border-white/[0.12] dark:hover:border-white/20";
  const textClass = dark ? "text-white/50" : "text-ink/50 dark:text-ink-dark/50";

  return (
    <div className="w-full">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragActive(false);
          const file = e.dataTransfer.files[0];
          if (file) void handleFile(file);
        }}
        onClick={() => inputRef.current?.click()}
        className={`flex cursor-pointer items-center justify-center gap-2 rounded-full border border-dashed px-5 py-2.5 text-[13px] transition ${textClass} ${
          dragActive ? "border-accent/50" : fieldClass
        }`}
      >
        Drop a .lrc or .srt file, or click to choose one
      </div>
      <input
        ref={inputRef}
        type="file"
        accept=".lrc,.srt"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) void handleFile(file);
          e.target.value = "";
        }}
      />
      {error && (
        <p className={`mt-2 text-[13px] ${dark ? "text-red-400/80" : "text-red-500/80"}`}>
          {error}
        </p>
      )}
    </div>
  );
}

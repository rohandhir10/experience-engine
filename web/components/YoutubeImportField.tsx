"use client";

import { useState } from "react";

// videoId is optional so InputScreen.tsx can reuse this same shape for
// lib/lyricsImport.ts's .lrc/.srt import, which has real per-section
// timing but no video to attach - see useAdaptSubmit.ts's YoutubeSource
// for the same generalization on the submit side.
export type YoutubeDraft = {
  videoId?: string;
  draftText: string;
  sections: { start: number; end: number }[];
  warning: string;
};

/** Fetches a video's own captions (server/main.py's /api/youtube-draft,
 * which wraps engine/youtube_ingest.py) and hands the result back as a
 * draft for the caller to drop into its normal lyrics textarea — this
 * component owns only the URL field and the fetch, not the review step.
 * Section boundaries here are a timing-gap guess, not real verse/chorus
 * structure (same caveat the CLI tool states), so onImported's caller is
 * expected to let the user edit the text before submitting it, not pipe
 * it straight to the engine. */
export function YoutubeImportField({
  onImported,
  dark = false,
}: {
  onImported: (draft: YoutubeDraft) => void;
  dark?: boolean;
}) {
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function fetchDraft() {
    if (!url.trim() || loading) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/youtube-draft", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(body.detail || body.error || "Could not read this video's captions.");
      }
      onImported({
        videoId: body.video_id,
        draftText: body.draft_text,
        sections: body.sections,
        warning: body.warning,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not read this video's captions.");
    } finally {
      setLoading(false);
    }
  }

  const fieldClass = dark
    ? "border-white/10 bg-white/[0.04] text-white placeholder:text-white/38 focus:border-white/20"
    : "border-black/[0.12] bg-white/70 text-ink placeholder:text-ink/45 focus:border-black/20 dark:border-white/[0.12] dark:bg-white/[0.03] dark:text-ink-dark dark:placeholder:text-ink-dark/45";
  const buttonClass = dark
    ? "border-white/15 text-white/80 hover:border-white/30 hover:text-white"
    : "border-black/10 text-ink/78 hover:border-black/20 hover:text-ink dark:border-white/10 dark:text-ink-dark/78";

  return (
    <div className="w-full">
      <div className="flex gap-2">
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              fetchDraft();
            }
          }}
          placeholder="Paste a YouTube link…"
          className={`min-w-0 flex-1 rounded-full border px-5 py-2.5 text-[14px] outline-none transition ${fieldClass}`}
        />
        <button
          type="button"
          onClick={fetchDraft}
          disabled={!url.trim() || loading}
          className={`shrink-0 rounded-full border px-5 py-2.5 text-[14px] font-medium transition disabled:cursor-not-allowed disabled:opacity-30 ${buttonClass}`}
        >
          {loading ? "Fetching…" : "Fetch lyrics"}
        </button>
      </div>
      {error && (
        <p className={`mt-2 text-[13px] ${dark ? "text-red-400/80" : "text-red-500/80"}`}>
          {error}
        </p>
      )}
    </div>
  );
}

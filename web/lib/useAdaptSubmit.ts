"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export type YoutubeSource = {
  videoId: string;
  sectionTimings: { start: number; end: number }[];
};

const POLL_INTERVAL_MS = 2_500;
// A full multi-section song can run several minutes (server/main.py's
// module docstring: each section is 3-7 sequential LLM calls) - generous
// on purpose, since the alternative to waiting is the exact serverless
// timeout /api/adapt/start exists to avoid.
const MAX_POLL_MS = 10 * 60 * 1000;

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/** Shared by every surface that can submit lyrics for adaptation (the
 * marketing homepage, the dashboard) so the fetch/stash/navigate flow
 * isn't duplicated — see app/page.tsx's original comments for why the
 * result is stashed in sessionStorage before navigating.
 *
 * Submits via /api/adapt/start rather than the older blocking /api/adapt:
 * that route returns almost immediately (a cache hit, or a job_id),
 * and this polls /api/adapt/jobs/[jobId] until the engine run finishes -
 * a full song routinely takes minutes, well past what a single Vercel
 * function invocation is allowed to block for. */
export function useAdaptSubmit() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function pollJob(jobId: string): Promise<Record<string, unknown>> {
    const deadline = Date.now() + MAX_POLL_MS;
    while (Date.now() < deadline) {
      await sleep(POLL_INTERVAL_MS);
      const res = await fetch(`/api/adapt/jobs/${jobId}`);
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(body.error || body.detail || "Something went wrong.");
      }
      if (body.status === "done") return body.result;
      if (body.status === "error") {
        throw new Error(body.error || "Something went wrong.");
      }
      // "pending" or "running" - keep polling.
    }
    throw new Error(
      "This song is taking longer than expected. Please try again in a few minutes."
    );
  }

  async function submit(
    text: string,
    targetLanguage: string = "English",
    sourceLanguage?: string,
    youtube?: YoutubeSource
  ) {
    setLoading(true);
    setError(null);
    try {
      const startRes = await fetch("/api/adapt/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text,
          target_language: targetLanguage,
          // Required by server/main.py for every target except English -
          // undefined here means "unspecified" (auto-detect), which is
          // only actually valid for the English-target direction.
          ...(sourceLanguage ? { source_language: sourceLanguage } : {}),
          // Only forwarded when the section count still matches what was
          // reviewed — if the user edited the draft's blank-line breaks,
          // youtube_section_timings.length no longer lines up with
          // anything real, and server/main.py drops it rather than guess.
          ...(youtube
            ? {
                youtube_video_id: youtube.videoId,
                youtube_section_timings: youtube.sectionTimings,
              }
            : {}),
        }),
      });
      const startBody = await startRes.json().catch(() => ({}));
      if (!startRes.ok) {
        throw new Error(startBody.error || startBody.detail || "Something went wrong.");
      }

      const result =
        startBody.status === "done" ? startBody.result : await pollJob(startBody.job_id);

      try {
        sessionStorage.setItem(`castia-result-${result.id}`, JSON.stringify(result));
      } catch {
        // Covered by the share page's network fallback.
      }
      router.push(`/s/${result.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
      setLoading(false);
    }
  }

  return { submit, loading, error };
}

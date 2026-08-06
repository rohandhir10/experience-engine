export type AdaptedPanel = {
  id: string;
  literal: string;
  adaptedText: string;
  why: string;
};

export type ChapterAdaptResult = {
  // server/cache.py::comics_content_id - a real, content-addressed,
  // persistent id, the same storage /api/adapt's result_id uses. Powers
  // /comics/s/[id] the same way a song's id powers /s/[id].
  id: string;
  panels: AdaptedPanel[];
};

/** One snapshot of an in-flight chapter job - server/jobs.py's
 * progress_json, as reported by server/main.py::_run_comics_adaptation
 * after every real, already-happening step (not a fabricated "analyzing
 * tone" style message - see that function's docstring). `panels` grows
 * with each completed panel, in order, so the UI can render a panel's
 * real adapted text the moment it's ready rather than waiting for the
 * whole chapter. */
export type ChapterAdaptProgress = {
  completed: number;
  total: number;
  message: string;
  panels: AdaptedPanel[];
};

export class AdaptRequestError extends Error {}

// Short enough that per-panel progress feels close to live without
// hammering the job-status endpoint - each poll is a fast lookup on
// server/jobs.py's side (in-memory dict or a single-row Postgres read),
// not a real cost concern at this interval.
const POLL_INTERVAL_MS = 1_500;
// A chapter runs one full Writers' Room per panel, sequentially (voice/
// honorific continuity - see server/main.py::_run_comics_adaptation's
// docstring on why panels aren't batched or parallelized), so a large
// chapter can take a while. Generous on purpose, same reasoning as
// lib/useAdaptSubmit.ts's MAX_POLL_MS for songs.
const MAX_POLL_MS = 15 * 60 * 1000;

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function toChapterAdaptResult(result: {
  id: string;
  panels: { id: string; literal: string; adapted_text: string; why: string }[];
}): ChapterAdaptResult {
  return {
    id: result.id,
    panels: toAdaptedPanels(result.panels),
  };
}

function toAdaptedPanels(
  panels: { id: string; literal: string; adapted_text: string; why: string }[] | undefined
): AdaptedPanel[] {
  return (panels ?? []).map((panel) => ({
    id: panel.id,
    literal: panel.literal,
    adaptedText: panel.adapted_text,
    why: panel.why,
  }));
}

async function pollJob(
  jobId: string,
  onProgress?: (progress: ChapterAdaptProgress) => void
): Promise<ChapterAdaptResult> {
  const deadline = Date.now() + MAX_POLL_MS;
  while (Date.now() < deadline) {
    await sleep(POLL_INTERVAL_MS);
    const res = await fetch(`/api/comics/adapt/jobs/${jobId}`);
    const body = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new AdaptRequestError(body.error || body.detail || "Adapting this chapter failed.");
    }
    if (body.status === "done") return toChapterAdaptResult(body.result);
    if (body.status === "error") {
      throw new AdaptRequestError(body.error || "Adapting this chapter failed.");
    }
    if (body.progress && onProgress) {
      onProgress({
        completed: body.progress.completed,
        total: body.progress.total,
        message: body.progress.message,
        panels: toAdaptedPanels(body.progress.panels),
      });
    }
    // "pending" or "running" - keep polling.
  }
  throw new AdaptRequestError(
    "This chapter is taking longer than expected. Please try again in a few minutes."
  );
}

// Calls app/api/comics/adapt/start/route.ts, which proxies to
// server/main.py's POST /api/comics/adapt/start (Chapter DNA +
// engine/comics_adapt.py, run in a background job rather than blocking
// this request - see that endpoint's docstring). Returns almost
// immediately with either a cached result or a job_id, then polls
// app/api/comics/adapt/jobs/[jobId]/route.ts until the engine run
// finishes - the same start+poll shape lib/useAdaptSubmit.ts already
// uses for songs, extended here so a large chapter can't hit a request
// timeout the way the older single-call /api/comics/adapt could.
//
// `onProgress`, when given, is called with each panel's real result as
// soon as it's ready (server/jobs.py's progress_json) - the caller can
// use this to unlock and render panels one at a time instead of staring
// at a single spinner for however long the whole chapter takes. Never
// called for a cache hit (status="done" immediately - nothing was ever
// "in progress").
//
// Callers build `panels` via lib/comics-types.ts::panelToChapterBubbles,
// which sends one adaptation unit per detected OCR region, not one per
// whole panel - a panel with several speech bubbles gets each adapted
// independently. `voice`, when set, becomes BubbleInput.voice
// server-side - the thing that actually drives per-character voice
// consistency and honorific-register tracking (engine/comics_adapt.py);
// omitted, a bubble is adapted unattributed.
export async function adaptChapter(
  panels: { id: string; text: string; voice?: string }[],
  sourceLanguage: string,
  targetLanguage: string,
  onProgress?: (progress: ChapterAdaptProgress) => void
): Promise<ChapterAdaptResult> {
  const res = await fetch("/api/comics/adapt/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      source_language: sourceLanguage,
      target_language: targetLanguage,
      panels,
    }),
  });
  const body = await res.json().catch(() => ({}));

  if (!res.ok) {
    throw new AdaptRequestError(body.error || body.detail || "Adapting this chapter failed.");
  }

  if (body.status === "done") return toChapterAdaptResult(body.result);
  return pollJob(body.job_id, onProgress);
}

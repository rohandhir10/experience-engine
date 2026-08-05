import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { adaptChapter, AdaptRequestError } from "./comicsAdapt";

function jsonResponse(body: unknown, ok = true) {
  return Promise.resolve({
    ok,
    json: () => Promise.resolve(body),
  } as Response);
}

describe("adaptChapter", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("returns immediately on a cache-hit (status: done) without polling", async () => {
    const fetchMock = vi.fn().mockReturnValue(
      jsonResponse({
        status: "done",
        job_id: null,
        result: { id: "chapter-1", panels: [{ id: "p1", literal: "hi", adapted_text: "hey", why: "casual" }] },
      })
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await adaptChapter([{ id: "p1", text: "hi" }], "Korean", "English");

    expect(result).toEqual({
      id: "chapter-1",
      panels: [{ id: "p1", literal: "hi", adaptedText: "hey", why: "casual" }],
    });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/comics/adapt/start",
      expect.objectContaining({ method: "POST" })
    );
  });

  it("polls the job until done, then returns the mapped result", async () => {
    const fetchMock = vi
      .fn()
      // POST /start -> pending
      .mockReturnValueOnce(jsonResponse({ status: "pending", job_id: "job-1", result: null }))
      // GET /jobs/job-1 -> still running
      .mockReturnValueOnce(jsonResponse({ status: "running", result: null, error: null }))
      // GET /jobs/job-1 -> done
      .mockReturnValueOnce(
        jsonResponse({
          status: "done",
          result: { id: "chapter-2", panels: [{ id: "p1", literal: "a", adapted_text: "b", why: "c" }] },
          error: null,
        })
      );
    vi.stubGlobal("fetch", fetchMock);

    const promise = adaptChapter([{ id: "p1", text: "hi" }], "Korean", "English");
    // Let both poll iterations' sleeps elapse.
    await vi.advanceTimersByTimeAsync(1_500);
    await vi.advanceTimersByTimeAsync(1_500);

    const result = await promise;
    expect(result.id).toBe("chapter-2");
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/api/comics/adapt/jobs/job-1");
  });

  it("throws AdaptRequestError when the job settles as an error", async () => {
    const fetchMock = vi
      .fn()
      .mockReturnValueOnce(jsonResponse({ status: "pending", job_id: "job-2", result: null }))
      .mockReturnValueOnce(
        jsonResponse({ status: "error", result: null, error: "The engine hit a problem." })
      );
    vi.stubGlobal("fetch", fetchMock);

    const promise = adaptChapter([{ id: "p1", text: "hi" }], "Korean", "English");
    const assertion = expect(promise).rejects.toThrow(AdaptRequestError);
    await vi.advanceTimersByTimeAsync(1_500);
    await assertion;
  });

  it("reports progress with each panel's real result as it arrives, but not on the terminal poll", async () => {
    const fetchMock = vi
      .fn()
      .mockReturnValueOnce(jsonResponse({ status: "pending", job_id: "job-3", result: null }))
      .mockReturnValueOnce(
        jsonResponse({
          status: "running",
          result: null,
          error: null,
          progress: {
            completed: 0,
            total: 2,
            message: "Panel 1/2: adapting…",
            panels: [],
          },
        })
      )
      .mockReturnValueOnce(
        jsonResponse({
          status: "running",
          result: null,
          error: null,
          progress: {
            completed: 1,
            total: 2,
            message: "Panel 1/2: done",
            panels: [{ id: "p1", literal: "a", adapted_text: "b", why: "c" }],
          },
        })
      )
      .mockReturnValueOnce(
        jsonResponse({
          status: "done",
          error: null,
          result: {
            id: "chapter-3",
            panels: [
              { id: "p1", literal: "a", adapted_text: "b", why: "c" },
              { id: "p2", literal: "d", adapted_text: "e", why: "f" },
            ],
          },
        })
      );
    vi.stubGlobal("fetch", fetchMock);

    const onProgress = vi.fn();
    const promise = adaptChapter([{ id: "p1", text: "hi" }], "Korean", "English", onProgress);
    await vi.advanceTimersByTimeAsync(1_500);
    await vi.advanceTimersByTimeAsync(1_500);
    await vi.advanceTimersByTimeAsync(1_500);
    const result = await promise;

    expect(result.panels).toHaveLength(2);
    // Called for the two "running" polls, never for the final "done" one -
    // that result comes back as the resolved promise instead.
    expect(onProgress).toHaveBeenCalledTimes(2);
    expect(onProgress).toHaveBeenNthCalledWith(1, {
      completed: 0,
      total: 2,
      message: "Panel 1/2: adapting…",
      panels: [],
    });
    expect(onProgress).toHaveBeenNthCalledWith(2, {
      completed: 1,
      total: 2,
      message: "Panel 1/2: done",
      panels: [{ id: "p1", literal: "a", adaptedText: "b", why: "c" }],
    });
  });

  it("throws AdaptRequestError immediately when /start itself fails", async () => {
    const fetchMock = vi.fn().mockReturnValue(jsonResponse({ error: "Too many chapters today." }, false));
    vi.stubGlobal("fetch", fetchMock);

    await expect(adaptChapter([{ id: "p1", text: "hi" }], "Korean", "English")).rejects.toThrow(
      "Too many chapters today."
    );
  });
});

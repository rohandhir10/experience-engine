import { describe, expect, it } from "vitest";
import { OCR_BATCH_CONCURRENCY, runWithConcurrency } from "./concurrency";

function deferred() {
  let resolve!: () => void;
  const promise = new Promise<void>((r) => {
    resolve = r;
  });
  return { promise, resolve };
}

describe("runWithConcurrency", () => {
  it("runs every item exactly once", async () => {
    const seen: number[] = [];
    await runWithConcurrency([1, 2, 3, 4, 5], 2, async (n) => {
      seen.push(n);
    });
    expect(seen.sort()).toEqual([1, 2, 3, 4, 5]);
  });

  it("never exceeds the concurrency limit", async () => {
    let inFlight = 0;
    let peak = 0;
    await runWithConcurrency(Array.from({ length: 20 }, (_, i) => i), 4, async () => {
      inFlight++;
      peak = Math.max(peak, inFlight);
      await new Promise((r) => setTimeout(r, 1));
      inFlight--;
    });
    expect(peak).toBeLessThanOrEqual(4);
  });

  it("actually runs work in parallel rather than serially", async () => {
    let peak = 0;
    let inFlight = 0;
    await runWithConcurrency([1, 2, 3, 4], 4, async () => {
      inFlight++;
      peak = Math.max(peak, inFlight);
      await new Promise((r) => setTimeout(r, 1));
      inFlight--;
    });
    expect(peak).toBeGreaterThan(1);
  });

  it("keeps other workers moving while one item is slow", async () => {
    // The chunking bug this guards against: with fixed chunks, a single
    // slow item blocks its whole batch and later items can't start.
    const slow = deferred();
    const finished: number[] = [];

    const run = runWithConcurrency([0, 1, 2, 3, 4, 5], 2, async (n) => {
      if (n === 0) {
        await slow.promise;
      }
      finished.push(n);
    });

    // Let the non-blocked worker chew through everything else.
    await new Promise((r) => setTimeout(r, 5));
    expect(finished).toEqual([1, 2, 3, 4, 5]);

    slow.resolve();
    await run;
    expect(finished.sort()).toEqual([0, 1, 2, 3, 4, 5]);
  });

  it("does not reject when a worker throws, and still runs the rest", async () => {
    const done: number[] = [];
    await expect(
      runWithConcurrency([1, 2, 3], 2, async (n) => {
        if (n === 2) throw new Error("panel unreadable");
        done.push(n);
      })
    ).resolves.toBeUndefined();
    expect(done.sort()).toEqual([1, 3]);
  });

  it("handles an empty list without hanging", async () => {
    await expect(runWithConcurrency([], 4, async () => {})).resolves.toBeUndefined();
  });

  it("treats a limit below 1 as 1 rather than spawning no workers", async () => {
    const seen: number[] = [];
    await runWithConcurrency([1, 2], 0, async (n) => {
      seen.push(n);
    });
    expect(seen).toEqual([1, 2]);
  });

  it("passes the item's index through", async () => {
    const pairs: [string, number][] = [];
    await runWithConcurrency(["a", "b"], 1, async (item, i) => {
      pairs.push([item, i]);
    });
    expect(pairs).toEqual([
      ["a", 0],
      ["b", 1],
    ]);
  });

  it("uses a batch size that is bounded but better than serial", () => {
    expect(OCR_BATCH_CONCURRENCY).toBeGreaterThan(1);
    expect(OCR_BATCH_CONCURRENCY).toBeLessThanOrEqual(8);
  });
});

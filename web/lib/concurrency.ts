// How many panels to OCR at once in a batch run. Bounded rather than
// unbounded on purpose: a chapter can be 40+ panels, and firing all of
// them simultaneously would open 40 uploads at once, hit the engine with
// 40 concurrent Cloud Vision calls, and be far more likely to trip a
// rate limit or a proxy connection cap than it would be to finish
// faster. Small enough to be polite, large enough that the wall-clock
// win over one-at-a-time is most of what's available.
export const OCR_BATCH_CONCURRENCY = 4;

/** Runs `worker` over every item with at most `limit` in flight at once.
 *
 * Never rejects: a worker that throws resolves to undefined for that
 * item and the rest of the batch continues. A batch action over a whole
 * chapter must not be all-or-nothing - one unreadable panel shouldn't
 * abandon the other thirty-nine, and each panel already records its own
 * error state for the human to see.
 */
export async function runWithConcurrency<T>(
  items: readonly T[],
  limit: number,
  worker: (item: T, index: number) => Promise<unknown>
): Promise<void> {
  if (items.length === 0) return;
  const effectiveLimit = Math.max(1, Math.min(limit, items.length));

  // A shared cursor rather than fixed-size chunks: with chunking, a
  // batch only advances when its SLOWEST member finishes, so one big
  // panel stalls three idle workers. Pulling from a cursor keeps every
  // worker busy until the queue is genuinely empty.
  let cursor = 0;
  async function drain(): Promise<void> {
    while (cursor < items.length) {
      const index = cursor++;
      try {
        await worker(items[index], index);
      } catch {
        // Recorded per-item by the worker itself; see doc comment.
      }
    }
  }

  await Promise.all(Array.from({ length: effectiveLimit }, drain));
}

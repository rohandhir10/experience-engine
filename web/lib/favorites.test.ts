import { describe, expect, it } from "vitest";
import { applyFavorite } from "./favorites";
import type { HistoryEntry } from "./history";

function entry(resultId: string, isFavorite = false): HistoryEntry {
  return {
    resultId,
    createdAt: "2026-08-04T00:00:00+00:00",
    isFavorite,
    hook: `hook for ${resultId}`,
    sourceLanguage: "Hindi",
    targetLanguage: "English",
    collectionIds: [],
  };
}

describe("applyFavorite", () => {
  it("flips only the targeted entry", () => {
    const result = applyFavorite([entry("a"), entry("b")], "b", true);
    expect(result.map((e) => e.isFavorite)).toEqual([false, true]);
  });

  it("rolls back cleanly (a second call with the old value restores it)", () => {
    const original = [entry("a", false)];
    const flipped = applyFavorite(original, "a", true);
    const rolledBack = applyFavorite(flipped, "a", false);
    expect(rolledBack).toEqual(original);
  });

  it("does not mutate the input array or its entries", () => {
    const original = [entry("a", false)];
    applyFavorite(original, "a", true);
    expect(original[0].isFavorite).toBe(false);
  });

  it("leaves an unfavorited row in place on the full history list", () => {
    const result = applyFavorite([entry("a", true), entry("b")], "a", false);
    expect(result.map((e) => e.resultId)).toEqual(["a", "b"]);
    expect(result[0].isFavorite).toBe(false);
  });

  it("drops an unfavorited row on the favorites page", () => {
    const result = applyFavorite([entry("a", true), entry("b", true)], "a", false, true);
    expect(result.map((e) => e.resultId)).toEqual(["b"]);
  });

  it("does not drop a row that is being favorited, even on the favorites page", () => {
    const result = applyFavorite([entry("a", false)], "a", true, true);
    expect(result).toHaveLength(1);
    expect(result[0].isFavorite).toBe(true);
  });

  it("is a no-op for an unknown result id", () => {
    const original = [entry("a")];
    expect(applyFavorite(original, "missing", true)).toEqual(original);
  });
});

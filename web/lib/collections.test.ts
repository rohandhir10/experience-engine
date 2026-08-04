import { describe, expect, it } from "vitest";
import {
  adjustCount,
  applyMembership,
  prepend,
  removeFrom,
  renameIn,
  type Collection,
} from "./collections";
import type { HistoryEntry } from "./history";

function collection(id: string, name = `name-${id}`, count = 0): Collection {
  return { id, name, count };
}

describe("renameIn", () => {
  it("renames only the targeted collection", () => {
    const result = renameIn([collection("a"), collection("b")], "b", "Renamed");
    expect(result.map((c) => c.name)).toEqual(["name-a", "Renamed"]);
  });

  it("does not mutate the input", () => {
    const original = [collection("a", "Before")];
    renameIn(original, "a", "After");
    expect(original[0].name).toBe("Before");
  });

  it("is a no-op for an unknown id", () => {
    const original = [collection("a")];
    expect(renameIn(original, "missing", "X")).toEqual(original);
  });
});

describe("removeFrom", () => {
  it("removes the targeted collection and leaves the rest", () => {
    const result = removeFrom([collection("a"), collection("b")], "a");
    expect(result.map((c) => c.id)).toEqual(["b"]);
  });

  it("is a no-op for an unknown id", () => {
    const original = [collection("a")];
    expect(removeFrom(original, "missing")).toEqual(original);
  });
});

describe("prepend", () => {
  it("puts a new collection first, matching the server's newest-first order", () => {
    const result = prepend([collection("a")], collection("new"));
    expect(result.map((c) => c.id)).toEqual(["new", "a"]);
  });
});

describe("adjustCount", () => {
  it("increments and decrements the targeted collection", () => {
    const start = [collection("a", "A", 2), collection("b", "B", 0)];
    expect(adjustCount(start, "a", 1)[0].count).toBe(3);
    expect(adjustCount(start, "a", -1)[0].count).toBe(1);
  });

  it("never renders a negative count", () => {
    const result = adjustCount([collection("a", "A", 0)], "a", -1);
    expect(result[0].count).toBe(0);
  });

  it("leaves other collections untouched", () => {
    const result = adjustCount([collection("a", "A", 5), collection("b", "B", 5)], "a", 1);
    expect(result[1].count).toBe(5);
  });
});

describe("applyMembership", () => {
  function entry(resultId: string, collectionIds: string[] = []): HistoryEntry {
    return {
      resultId,
      createdAt: "2026-08-04T00:00:00+00:00",
      isFavorite: false,
      medium: "music",
      hook: null,
      sourceLanguage: null,
      targetLanguage: null,
      collectionIds,
    };
  }

  it("adds a collection id to the targeted entry only", () => {
    const result = applyMembership([entry("a"), entry("b")], "a", "c1", true);
    expect(result[0].collectionIds).toEqual(["c1"]);
    expect(result[1].collectionIds).toEqual([]);
  });

  it("removes a collection id", () => {
    const result = applyMembership([entry("a", ["c1", "c2"])], "a", "c1", false);
    expect(result[0].collectionIds).toEqual(["c2"]);
  });

  it("does not duplicate on a repeated add", () => {
    const once = applyMembership([entry("a")], "a", "c1", true);
    const twice = applyMembership(once, "a", "c1", true);
    expect(twice[0].collectionIds).toEqual(["c1"]);
  });

  it("removing something that was never there is a no-op", () => {
    const result = applyMembership([entry("a", ["c2"])], "a", "c1", false);
    expect(result[0].collectionIds).toEqual(["c2"]);
  });

  it("does not mutate the input entry", () => {
    const original = [entry("a", [])];
    applyMembership(original, "a", "c1", true);
    expect(original[0].collectionIds).toEqual([]);
  });
});

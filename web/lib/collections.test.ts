import { describe, expect, it } from "vitest";
import { adjustCount, prepend, removeFrom, renameIn, type Collection } from "./collections";

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

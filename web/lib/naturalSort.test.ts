import { describe, expect, it } from "vitest";
import { naturalCompare } from "./naturalSort";

describe("naturalCompare", () => {
  it("orders numeric chapter-slice names by value, not lexically", () => {
    const names = ["panel-10.jpg", "panel-2.jpg", "panel-1.jpg"];
    expect([...names].sort(naturalCompare)).toEqual([
      "panel-1.jpg",
      "panel-2.jpg",
      "panel-10.jpg",
    ]);
  });

  it("falls back to plain comparison when there are no digits", () => {
    const names = ["cover.jpg", "back.jpg"];
    expect([...names].sort(naturalCompare)).toEqual(["back.jpg", "cover.jpg"]);
  });

  it("handles zero-padded numbers the same as unpadded ones", () => {
    const names = ["003.png", "1.png", "02.png"];
    expect([...names].sort(naturalCompare)).toEqual(["1.png", "02.png", "003.png"]);
  });
});

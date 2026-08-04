import { describe, expect, it } from "vitest";
import { resolveHistoryEntryDisplay } from "./historyEntryDisplay";

describe("resolveHistoryEntryDisplay", () => {
  it("links a music entry to /s/[id] and keeps its hook line", () => {
    const result = resolveHistoryEntryDisplay({
      resultId: "song-1",
      medium: "music",
      hook: "Stay — one breath, steady this heart.",
    });
    expect(result).toEqual({
      label: "Stay — one breath, steady this heart.",
      href: "/s/song-1",
    });
  });

  it("falls back to 'Untitled adaptation' for a music entry with no hook", () => {
    const result = resolveHistoryEntryDisplay({ resultId: "song-2", medium: "music", hook: null });
    expect(result.label).toBe("Untitled adaptation");
  });

  it("links a webtoons entry to /comics/s/[id]", () => {
    const result = resolveHistoryEntryDisplay({
      resultId: "chapter-1",
      medium: "webtoons",
      hook: null,
    });
    expect(result).toEqual({ label: "Adapted chapter", href: "/comics/s/chapter-1" });
  });

  it("never expects a webtoons entry to have a hook, but would still show it if one existed", () => {
    // The comics wire shape never produces a hook today - this just
    // documents that the fallback is hook-first, not medium-first, in
    // case that ever changes.
    const result = resolveHistoryEntryDisplay({
      resultId: "chapter-2",
      medium: "webtoons",
      hook: "unexpected but should still win",
    });
    expect(result.label).toBe("unexpected but should still win");
  });
});

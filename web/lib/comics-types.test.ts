import { describe, expect, it } from "vitest";
import {
  applyBubbleResult,
  combinedAdaptedText,
  combinedWhy,
  moveItem,
  ocrRerunWouldDiscardWork,
  panelAdaptStatus,
  panelToChapterBubbles,
  panelsToCsv,
  parseBubbleId,
  type ComicPanel,
  type OcrRegion,
} from "./comics-types";

function panel(overrides: Partial<ComicPanel> = {}): ComicPanel {
  return {
    id: "1",
    fileName: "panel-1.jpg",
    file: new File([], "panel-1.jpg"),
    previewUrl: "blob:mock",
    extractedText: "",
    adaptedText: "",
    why: "",
    ocrStatus: "idle",
    ocrRegions: null,
    ocrMessage: null,
    detectedLanguages: null,
    voice: null,
    regionAdaptedTexts: null,
    regionWhys: null,
    redrawRegionTexts: null,
    redrawFont: null,
    redrawRegionFonts: null,
    redrawResultUrl: null,
    redrawResultId: null,
    redrawStatus: "idle",
    redrawMessage: null,
    ...overrides,
  };
}

function region(overrides: Partial<OcrRegion> = {}): OcrRegion {
  return {
    text: "source line",
    bbox: { x: 0, y: 0, width: 10, height: 10 },
    confidence: 90,
    ...overrides,
  };
}

describe("moveItem", () => {
  it("moves an item forward", () => {
    expect(moveItem(["a", "b", "c", "d"], 0, 2)).toEqual(["b", "c", "a", "d"]);
  });

  it("moves an item backward", () => {
    expect(moveItem(["a", "b", "c", "d"], 3, 1)).toEqual(["a", "d", "b", "c"]);
  });

  it("clamps a too-large toIndex to the end instead of throwing", () => {
    expect(moveItem(["a", "b", "c"], 0, 99)).toEqual(["b", "c", "a"]);
  });

  it("clamps a negative toIndex to the start instead of throwing", () => {
    expect(moveItem(["a", "b", "c"], 2, -5)).toEqual(["c", "a", "b"]);
  });

  it("returns the same array unchanged when fromIndex equals the clamped toIndex", () => {
    const original = ["a", "b", "c"];
    expect(moveItem(original, 1, 1)).toBe(original);
  });

  it("returns the same array unchanged for an out-of-range fromIndex", () => {
    const original = ["a", "b", "c"];
    expect(moveItem(original, 10, 0)).toBe(original);
    expect(moveItem(original, -1, 0)).toBe(original);
  });

  it("does not mutate the input array", () => {
    const original = ["a", "b", "c"];
    moveItem(original, 0, 2);
    expect(original).toEqual(["a", "b", "c"]);
  });
});

describe("panelsToCsv", () => {
  it("writes a header row and one row per panel, numbered from 1", () => {
    const csv = panelsToCsv([
      panel({ fileName: "a.jpg", extractedText: "hello" }),
      panel({ fileName: "b.jpg", extractedText: "world" }),
    ]);
    const lines = csv.split("\n");
    expect(lines[0]).toBe("panel,file_name,voice,extracted_text,adapted_text,why");
    expect(lines[1]).toContain('"1"');
    expect(lines[1]).toContain('"a.jpg"');
    expect(lines[2]).toContain('"2"');
    expect(lines[2]).toContain('"world"');
  });

  it("escapes embedded quotes so the CSV stays parseable", () => {
    const csv = panelsToCsv([panel({ extractedText: 'she said "hi"' })]);
    expect(csv).toContain('"she said ""hi"""');
  });

  it("writes an empty voice cell when unattributed, and the name when set", () => {
    const csv = panelsToCsv([panel({ voice: null }), panel({ voice: "Guard Captain" })]);
    const lines = csv.split("\n");
    expect(lines[1]).toContain('""');
    expect(lines[2]).toContain('"Guard Captain"');
  });

  it("exports the combined per-region adapted text for a panel with real regions", () => {
    const csv = panelsToCsv([
      panel({
        ocrRegions: [region(), region()],
        regionAdaptedTexts: ["first bubble adapted", "second bubble adapted"],
      }),
    ]);
    expect(csv).toContain('"first bubble adapted\n\nsecond bubble adapted"');
  });
});

// --- panelToChapterBubbles: the actual multi-bubble fix -------------------

describe("panelToChapterBubbles", () => {
  it("sends one bubble per detected region instead of flattening them", () => {
    const p = panel({
      ocrRegions: [region({ text: "hello there" }), region({ text: "general kenobi" })],
    });
    const bubbles = panelToChapterBubbles(p);
    expect(bubbles).toEqual([
      { id: "1::0", text: "hello there", voice: undefined },
      { id: "1::1", text: "general kenobi", voice: undefined },
    ]);
  });

  it("prefers a region's own detected speaker over the panel-level voice", () => {
    const p = panel({
      voice: "Narrator",
      ocrRegions: [
        region({ text: "line one", speaker: "Guard Captain" }),
        region({ text: "line two", speaker: null }),
      ],
    });
    const bubbles = panelToChapterBubbles(p);
    expect(bubbles[0].voice).toBe("Guard Captain");
    // No region-level speaker - falls back to the panel-level voice.
    expect(bubbles[1].voice).toBe("Narrator");
  });

  it("drops a region with only whitespace text rather than sending an empty bubble", () => {
    const p = panel({ ocrRegions: [region({ text: "real line" }), region({ text: "   " })] });
    const bubbles = panelToChapterBubbles(p);
    expect(bubbles).toHaveLength(1);
    expect(bubbles[0].text).toBe("real line");
  });

  it("falls back to the flat extractedText as one bubble when there are no detected regions", () => {
    const p = panel({ ocrRegions: null, extractedText: "hand-typed dialogue", voice: "Someone" });
    expect(panelToChapterBubbles(p)).toEqual([
      { id: "1", text: "hand-typed dialogue", voice: "Someone" },
    ]);
  });

  it("returns nothing for a panel with no regions and no extracted text", () => {
    expect(panelToChapterBubbles(panel({ ocrRegions: null, extractedText: "   " }))).toEqual([]);
  });

  it("threads a region's kind through, for the SFX/background skip guard server-side", () => {
    const p = panel({
      ocrRegions: [region({ text: "BOOM", kind: "sfx" }), region({ text: "hello", kind: "dialogue" })],
    });
    const bubbles = panelToChapterBubbles(p);
    expect(bubbles[0].kind).toBe("sfx");
    expect(bubbles[1].kind).toBe("dialogue");
  });

  it("leaves kind undefined for a region with no vision-LLM classification", () => {
    const p = panel({ ocrRegions: [region({ text: "hello there" })] });
    expect(panelToChapterBubbles(p)[0].kind).toBeUndefined();
  });
});

describe("parseBubbleId", () => {
  it("splits a region bubble id into its panel id and region index", () => {
    expect(parseBubbleId("panel-42::3")).toEqual({ panelId: "panel-42", regionIndex: 3 });
  });

  it("treats a plain panel id (no separator) as the whole-panel flat bubble", () => {
    expect(parseBubbleId("panel-42")).toEqual({ panelId: "panel-42", regionIndex: null });
  });

  it("handles a panel id that itself legitimately contains '::' before the real separator", () => {
    expect(parseBubbleId("weird::name::2")).toEqual({ panelId: "weird::name", regionIndex: 2 });
  });

  it("falls back to treating the whole thing as a flat panel id when the suffix isn't a real index", () => {
    expect(parseBubbleId("panel-42::not-a-number")).toEqual({ panelId: "panel-42::not-a-number", regionIndex: null });
  });
});

describe("applyBubbleResult", () => {
  it("fills in the matching region's adapted text and why, leaving other regions untouched", () => {
    const p = panel({ id: "p1", ocrRegions: [region(), region()] });
    const updated = applyBubbleResult(p, "p1::1", { adaptedText: "adapted", why: "reason" });
    expect(updated.regionAdaptedTexts).toEqual([null, "adapted"]);
    expect(updated.regionWhys).toEqual([null, "reason"]);
  });

  it("returns the exact same panel object when the bubble id belongs to a different panel", () => {
    const p = panel({ id: "p1", ocrRegions: [region()] });
    const result = applyBubbleResult(p, "p2::0", { adaptedText: "x", why: "y" });
    expect(result).toBe(p);
  });

  it("never overwrites a region the human already filled in by hand", () => {
    const p = panel({
      id: "p1",
      ocrRegions: [region()],
      regionAdaptedTexts: ["human's own edit"],
    });
    const updated = applyBubbleResult(p, "p1::0", { adaptedText: "machine result", why: "reason" });
    expect(updated.regionAdaptedTexts).toEqual(["human's own edit"]);
  });

  it("applies a flat (no-region) bubble result to the panel's whole adaptedText/why", () => {
    const p = panel({ id: "p1", ocrRegions: null });
    const updated = applyBubbleResult(p, "p1", { adaptedText: "adapted", why: "reason" });
    expect(updated.adaptedText).toBe("adapted");
    expect(updated.why).toBe("reason");
  });

  it("ignores a region index that's out of range for this panel's current regions", () => {
    const p = panel({ id: "p1", ocrRegions: [region()] });
    const result = applyBubbleResult(p, "p1::5", { adaptedText: "x", why: "y" });
    expect(result).toBe(p);
  });
});

describe("combinedAdaptedText / combinedWhy", () => {
  it("joins real per-region results in order, skipping unfilled regions", () => {
    const p = panel({
      ocrRegions: [region(), region(), region()],
      regionAdaptedTexts: ["first", null, "third"],
      regionWhys: ["why one", null, "why three"],
    });
    expect(combinedAdaptedText(p)).toBe("first\n\nthird");
    expect(combinedWhy(p)).toBe("why one / why three");
  });

  it("falls back to the flat fields for a panel with no detected regions", () => {
    const p = panel({ ocrRegions: null, adaptedText: "flat adapted", why: "flat why" });
    expect(combinedAdaptedText(p)).toBe("flat adapted");
    expect(combinedWhy(p)).toBe("flat why");
  });
});

describe("panelAdaptStatus", () => {
  it("is 'none' for a panel with no real bubbles at all", () => {
    const p = panel({ ocrRegions: null, extractedText: "" });
    expect(panelAdaptStatus(p)).toBe("none");
  });

  it("is 'none' for a multi-region panel where nothing has been adapted yet", () => {
    const p = panel({ ocrRegions: [region(), region()] });
    expect(panelAdaptStatus(p)).toBe("none");
  });

  it("is 'partial' when some but not all regions have a real result", () => {
    const p = panel({
      ocrRegions: [region(), region(), region()],
      regionAdaptedTexts: ["one", null, null],
    });
    expect(panelAdaptStatus(p)).toBe("partial");
  });

  it("is 'done' once every region has a real, non-blank result", () => {
    const p = panel({
      ocrRegions: [region(), region()],
      regionAdaptedTexts: ["one", "two"],
    });
    expect(panelAdaptStatus(p)).toBe("done");
  });

  it("treats a whitespace-only region result the same as unfilled", () => {
    const p = panel({
      ocrRegions: [region(), region()],
      regionAdaptedTexts: ["one", "   "],
    });
    expect(panelAdaptStatus(p)).toBe("partial");
  });

  it("for a no-region (flat) panel, is 'done' once adaptedText is filled and 'none' otherwise", () => {
    const empty = panel({ ocrRegions: null, extractedText: "hand-typed line", adaptedText: "" });
    expect(panelAdaptStatus(empty)).toBe("none");

    const filled = panel({
      ocrRegions: null,
      extractedText: "hand-typed line",
      adaptedText: "adapted line",
    });
    expect(panelAdaptStatus(filled)).toBe("done");
  });
});

describe("ocrRerunWouldDiscardWork", () => {
  it("is false before OCR has ever run - nothing to lose yet", () => {
    const p = panel({ ocrStatus: "idle" });
    expect(ocrRerunWouldDiscardWork(p)).toBe(false);
  });

  it("is false while OCR is actively running", () => {
    const p = panel({ ocrStatus: "running", regionAdaptedTexts: ["a real result"] });
    expect(ocrRerunWouldDiscardWork(p)).toBe(false);
  });

  it("is false for a completed OCR run with nothing downstream filled in", () => {
    const p = panel({ ocrStatus: "done", ocrRegions: [region()] });
    expect(ocrRerunWouldDiscardWork(p)).toBe(false);
  });

  it("is true when a completed run has a real per-region adapted text", () => {
    const p = panel({ ocrStatus: "done", regionAdaptedTexts: [null, "real result"] });
    expect(ocrRerunWouldDiscardWork(p)).toBe(true);
  });

  it("is true when a completed run has a real per-region why", () => {
    const p = panel({ ocrStatus: "done", regionWhys: ["a reason"] });
    expect(ocrRerunWouldDiscardWork(p)).toBe(true);
  });

  it("is true when a completed run has a redraw text override", () => {
    const p = panel({ ocrStatus: "done", redrawRegionTexts: ["typed redraw text"] });
    expect(ocrRerunWouldDiscardWork(p)).toBe(true);
  });

  it("is true when a completed run already produced a redraw result", () => {
    const p = panel({ ocrStatus: "done", redrawResultUrl: "data:image/png;base64,abc" });
    expect(ocrRerunWouldDiscardWork(p)).toBe(true);
  });

  it("is true for a run that ended in error but still left real downstream work behind", () => {
    // e.g. OCR errored on a RERUN, but the panel already had real results
    // from the earlier successful run before that.
    const p = panel({ ocrStatus: "error", regionAdaptedTexts: ["kept from an earlier run"] });
    expect(ocrRerunWouldDiscardWork(p)).toBe(true);
  });
});

import { describe, expect, it } from "vitest";
import {
  applyBubbleResult,
  combinedAdaptedText,
  combinedWhy,
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

import { describe, expect, it, vi } from "vitest";
import { UNSAFE_REDRAW_KINDS, redrawPanel, resolveRedrawRegionText } from "./comicsRedraw";

function panel(overrides: {
  redrawRegionTexts?: (string | null)[] | null;
  ocrRegions?: { text: string; bbox: { x: number; y: number; width: number; height: number }; confidence: number }[] | null;
  adaptedText?: string;
  regionAdaptedTexts?: (string | null)[] | null;
}) {
  return {
    redrawRegionTexts: overrides.redrawRegionTexts ?? null,
    ocrRegions: overrides.ocrRegions ?? null,
    adaptedText: overrides.adaptedText ?? "",
    regionAdaptedTexts: overrides.regionAdaptedTexts ?? null,
  };
}

const region = {
  text: "source",
  bbox: { x: 0, y: 0, width: 10, height: 10 },
  confidence: 90,
};

describe("resolveRedrawRegionText", () => {
  it("defaults a single-region panel's unfilled slot to the whole adaptedText when there's no real per-region result yet", () => {
    const p = panel({ ocrRegions: [region], adaptedText: "the adapted line" });
    expect(resolveRedrawRegionText(p, 0)).toBe("the adapted line");
  });

  it("shows nothing for a multi-region panel with no real result and nothing typed yet", () => {
    const p = panel({ ocrRegions: [region, region], adaptedText: "the adapted line" });
    expect(resolveRedrawRegionText(p, 0)).toBe("");
    expect(resolveRedrawRegionText(p, 1)).toBe("");
  });

  it("uses each region's own real per-bubble adaptation result, not a guess", () => {
    const p = panel({
      ocrRegions: [region, region],
      regionAdaptedTexts: ["first bubble's real result", "second bubble's real result"],
    });
    expect(resolveRedrawRegionText(p, 0)).toBe("first bubble's real result");
    expect(resolveRedrawRegionText(p, 1)).toBe("second bubble's real result");
  });

  it("prefers a human override over a real per-region result", () => {
    const p = panel({
      ocrRegions: [region],
      regionAdaptedTexts: ["the real result"],
      redrawRegionTexts: ["a manually typed override"],
    });
    expect(resolveRedrawRegionText(p, 0)).toBe("a manually typed override");
  });

  it("prefers a human override over the single-region flat-text default", () => {
    const p = panel({
      ocrRegions: [region],
      adaptedText: "the adapted line",
      redrawRegionTexts: ["a manually typed override"],
    });
    expect(resolveRedrawRegionText(p, 0)).toBe("a manually typed override");
  });

  it("respects a per-region override in a multi-region panel, leaving others blank", () => {
    const p = panel({
      ocrRegions: [region, region, region],
      redrawRegionTexts: [null, "second region's text", null],
    });
    expect(resolveRedrawRegionText(p, 0)).toBe("");
    expect(resolveRedrawRegionText(p, 1)).toBe("second region's text");
    expect(resolveRedrawRegionText(p, 2)).toBe("");
  });

  it("an explicit empty-string override wins over the single-region default", () => {
    // Distinguishing "no override" (null) from "human cleared the field"
    // (empty string) matters: clearing a single-region default should
    // stick, not silently repopulate from adaptedText.
    const p = panel({
      ocrRegions: [region],
      adaptedText: "the adapted line",
      redrawRegionTexts: [""],
    });
    expect(resolveRedrawRegionText(p, 0)).toBe("");
  });

  it("returns empty for a panel with no OCR regions at all", () => {
    const p = panel({ ocrRegions: null, adaptedText: "something" });
    expect(resolveRedrawRegionText(p, 0)).toBe("");
  });
});

describe("UNSAFE_REDRAW_KINDS", () => {
  it("matches engine/comics_redraw.py's UNSAFE_REDRAW_KINDS exactly", () => {
    expect(UNSAFE_REDRAW_KINDS).toEqual(new Set(["sfx", "background"]));
  });
});

describe("redrawPanel", () => {
  function mockFetchOk() {
    return vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ image_base64: "abc123", id: "result-id" }),
    });
  }

  it("forwards each region's kind in the JSON body sent to the server", async () => {
    const fetchMock = mockFetchOk();
    vi.stubGlobal("fetch", fetchMock);

    await redrawPanel(new File([], "panel.png"), [
      { bbox: region.bbox, adaptedText: "hello", kind: "dialogue" },
      { bbox: region.bbox, adaptedText: "world" },
    ]);

    const form = fetchMock.mock.calls[0][1].body as FormData;
    const sentRegions = JSON.parse(form.get("regions") as string);
    expect(sentRegions).toEqual([
      { bbox: region.bbox, adapted_text: "hello", font: null, kind: "dialogue" },
      { bbox: region.bbox, adapted_text: "world", font: null, kind: null },
    ]);

    vi.unstubAllGlobals();
  });
});

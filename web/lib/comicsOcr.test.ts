import { describe, expect, it } from "vitest";
import { resolvePanelSpeaker } from "./comicsOcr";
import type { OcrRegion } from "./comics-types";

function region(partial: Partial<OcrRegion>): OcrRegion {
  return {
    text: "line",
    bbox: { x: 0, y: 0, width: 10, height: 10 },
    confidence: 90,
    ...partial,
  };
}

describe("resolvePanelSpeaker", () => {
  it("returns the speaker when the panel has exactly one", () => {
    const regions = [
      region({ kind: "dialogue", speaker: "Mira" }),
      region({ kind: "dialogue", speaker: "Mira" }),
    ];
    expect(resolvePanelSpeaker(regions)).toBe("Mira");
  });

  it("refuses to choose when two characters speak in one panel", () => {
    // Picking either would attribute half the lines to the wrong
    // character, and voice drives consistency for the whole chapter.
    const regions = [
      region({ kind: "dialogue", speaker: "Mira" }),
      region({ kind: "dialogue", speaker: "Jae" }),
    ];
    expect(resolvePanelSpeaker(regions)).toBeNull();
  });

  it("ignores sfx and background text when deciding", () => {
    const regions = [
      region({ kind: "dialogue", speaker: "Mira" }),
      region({ kind: "sfx", speaker: "Jae" }),
      region({ kind: "background", speaker: "Someone" }),
    ];
    expect(resolvePanelSpeaker(regions)).toBe("Mira");
  });

  it("returns null when no speaker was attributed", () => {
    expect(resolvePanelSpeaker([region({ kind: "dialogue", speaker: null })])).toBeNull();
  });

  it("returns null for a plain Cloud Vision result with no vision pass", () => {
    // The default path: no kind, no speaker on any region.
    expect(resolvePanelSpeaker([region({}), region({})])).toBeNull();
  });

  it("treats a whitespace-only speaker as no speaker", () => {
    expect(resolvePanelSpeaker([region({ kind: "dialogue", speaker: "   " })])).toBeNull();
  });

  it("returns null for an empty panel", () => {
    expect(resolvePanelSpeaker([])).toBeNull();
  });
});

import { describe, expect, it } from "vitest";
import { panelsToCsv, type ComicPanel } from "./comics-types";

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
});

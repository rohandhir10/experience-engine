// A single chapter-slice image plus whatever script text has been drawn
// out of it so far. There is no OCR or comics reasoning-engine backend
// yet (see app/comics/page.tsx's banner) - extractedText/adaptedText/why
// are plain user-editable fields, not model output, until that lands.
export type ComicPanel = {
  id: string;
  fileName: string;
  // A blob: URL for the file the user dropped in - never uploaded
  // anywhere, held only in this tab's memory for the session.
  previewUrl: string;
  extractedText: string;
  adaptedText: string;
  why: string;
};

export function panelToCsvRow(panel: ComicPanel, index: number): string {
  const cell = (value: string) => `"${value.replace(/"/g, '""')}"`;
  return [index + 1, panel.fileName, panel.extractedText, panel.adaptedText, panel.why]
    .map((value) => cell(String(value)))
    .join(",");
}

export function panelsToCsv(panels: ComicPanel[]): string {
  const header = ["panel", "file_name", "extracted_text", "adapted_text", "why"].join(",");
  return [header, ...panels.map((panel, index) => panelToCsvRow(panel, index))].join("\n");
}

"use client";

// pdfjs-dist is imported dynamically inside pdfToImageFiles, not at
// module scope - its main entry references browser-only globals
// (DOMMatrix) at import time, which crashes Next's server-side
// prerendering of any page that reaches this module (this file is
// "use client", but client components are still evaluated once during
// SSR/static export before hydration). A dynamic import's body only
// runs when the function is actually called, and this function is only
// ever called from a browser event handler (PanelUploader.tsx), so it
// never executes during the server-side pass.

// ~2x a PDF's defined point size lands close to the resolution a
// photographed or scanned panel image already arrives at in this
// workspace - enough for Cloud Vision OCR to read clean text without
// producing multi-page-spread-sized files for every panel.
const RENDER_SCALE = 2;

let workerConfigured = false;

export class PdfConversionError extends Error {
  constructor(
    public fileName: string,
    message: string
  ) {
    super(message);
    this.name = "PdfConversionError";
  }
}

/** Renders every page of one PDF to a PNG File, named so naturalCompare
 * (lib/naturalSort.ts) orders them the same way numbered image panels
 * already sort - page 2 before page 10. `onPage` reports progress for a
 * UI that wants to show it; multi-page PDFs can take several seconds. */
export async function pdfToImageFiles(
  pdfFile: File,
  onPage?: (pageNumber: number, totalPages: number) => void
): Promise<File[]> {
  // legacy/, not the default modern build - see scripts/copy-pdf-worker.js
  // for why (a very new JS engine feature the modern build depends on
  // threw at runtime on a real, current browser during testing).
  const pdfjsLib = await import("pdfjs-dist/legacy/build/pdf.mjs");

  if (!workerConfigured) {
    // Served from public/ (copied there by scripts/copy-pdf-worker.js on
    // every `npm install`) rather than resolved via
    // `new URL(..., import.meta.url)` - that's the usual bundler-asset
    // pattern, but Next's webpack config tries to parse and re-minify
    // this file as a normal JS module instead of copying it untouched,
    // and fails on the already-minified file's own `import.meta`
    // ("cannot be used outside of module code"). A plain public/ path
    // skips the bundler for this file entirely, and keeps this working
    // offline, unlike pointing at a CDN.
    pdfjsLib.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";
    workerConfigured = true;
  }

  const baseName = pdfFile.name.replace(/\.pdf$/i, "");
  let pdf;
  try {
    const buffer = await pdfFile.arrayBuffer();
    pdf = await pdfjsLib.getDocument({ data: buffer }).promise;
  } catch (err) {
    throw new PdfConversionError(
      pdfFile.name,
      err instanceof Error ? err.message : "Could not open this PDF"
    );
  }

  const files: File[] = [];
  for (let pageNumber = 1; pageNumber <= pdf.numPages; pageNumber++) {
    onPage?.(pageNumber, pdf.numPages);
    const page = await pdf.getPage(pageNumber);
    const viewport = page.getViewport({ scale: RENDER_SCALE });
    const canvas = document.createElement("canvas");
    canvas.width = viewport.width;
    canvas.height = viewport.height;
    const context = canvas.getContext("2d");
    if (!context) {
      throw new PdfConversionError(pdfFile.name, "Canvas rendering isn't available in this browser");
    }
    await page.render({ canvas, canvasContext: context, viewport }).promise;

    const blob: Blob | null = await new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
    if (!blob) {
      throw new PdfConversionError(pdfFile.name, `Could not render page ${pageNumber}`);
    }

    files.push(
      new File([blob], `${baseName}-page-${pageNumber}.png`, {
        type: "image/png",
        lastModified: pdfFile.lastModified,
      })
    );
  }

  return files;
}

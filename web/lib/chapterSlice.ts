"use client";

// A webtoon chapter uploaded as ONE tall image (an unsliced raw export,
// not the per-page cuts a platform normally hands out) used to reach
// the workspace as a single "panel" - and get silently ruined by it.
// lib/imageDownscale.ts's OCR_MAX_EDGE_PX (2000px) exists to shrink a
// NORMAL panel/page down to what Cloud Vision needs; run against a real
// chapter strip (routinely 15,000-50,000px tall), that same shrink
// crushes every speech bubble down to a few unreadable pixels before
// OCR ever sees it - no error, no warning, just wrong or missing text.
// Slicing here, before a strip ever becomes a "panel", is what actually
// fixes it, rather than rejecting the upload and pushing the same manual
// slicing work back onto the user.

/** Height/width past which an image reads as an unsliced whole-chapter
 * strip rather than a single (possibly tall) page. A real single page -
 * even an extra-tall spread - doesn't get close to this; a chapter strip
 * routinely runs 10-40x. Paired with SLICE_MIN_HEIGHT_PX so a small,
 * simply narrow image (an icon, a cropped detail) can't trip it purely
 * on ratio. */
export const SLICE_ASPECT_THRESHOLD = 3;

/** Minimum absolute height (px) before slicing kicks in at all - see
 * SLICE_ASPECT_THRESHOLD. */
export const SLICE_MIN_HEIGHT_PX = 4000;

/** Target height/width ratio for each resulting slice - close to a
 * normal manga/webtoon page, so each slice OCRs and redraws like any
 * other page in the workspace instead of needing special-casing. */
const TARGET_SLICE_ASPECT = 1.4;

const OUTPUT_MIME = "image/jpeg";
const OUTPUT_QUALITY = 0.92;

export class ChapterSliceError extends Error {
  constructor(
    public fileName: string,
    message: string
  ) {
    super(message);
    this.name = "ChapterSliceError";
  }
}

/** Whether an image this size should be auto-sliced into pages, and the
 * pixel height of each slice if so. Pure and DOM-free so it's directly
 * testable - the actual canvas cutting in sliceChapterStrip is not. */
export function planChapterSlices(
  width: number,
  height: number
): { shouldSlice: boolean; sliceHeight: number; count: number } {
  if (width <= 0 || height <= 0 || height / width < SLICE_ASPECT_THRESHOLD || height < SLICE_MIN_HEIGHT_PX) {
    return { shouldSlice: false, sliceHeight: height, count: 1 };
  }
  const sliceHeight = Math.round(width * TARGET_SLICE_ASPECT);
  return { shouldSlice: true, sliceHeight, count: Math.ceil(height / sliceHeight) };
}

/** Slices one unsliced whole-chapter image into page-sized Files, named
 * so naturalCompare (lib/naturalSort.ts) keeps them in reading order.
 * Returns the original file unchanged (as a one-element array) when
 * planChapterSlices says slicing isn't warranted - the common case of a
 * normal single page, which callers can treat identically either way. */
export async function sliceChapterStrip(file: File): Promise<File[]> {
  if (typeof createImageBitmap !== "function" || typeof document === "undefined") {
    return [file];
  }

  let bitmap: ImageBitmap;
  try {
    bitmap = await createImageBitmap(file);
  } catch (err) {
    throw new ChapterSliceError(file.name, err instanceof Error ? err.message : "Could not read this image");
  }

  try {
    const { shouldSlice, sliceHeight, count } = planChapterSlices(bitmap.width, bitmap.height);
    if (!shouldSlice) return [file];

    const baseName = file.name.replace(/\.[^.]+$/, "");
    const digits = String(count).length;
    const files: File[] = [];

    for (let i = 0; i < count; i++) {
      const y = i * sliceHeight;
      const thisSliceHeight = Math.min(sliceHeight, bitmap.height - y);

      const canvas = document.createElement("canvas");
      canvas.width = bitmap.width;
      canvas.height = thisSliceHeight;
      const ctx = canvas.getContext("2d");
      if (!ctx) throw new ChapterSliceError(file.name, "Canvas rendering isn't available in this browser");
      ctx.drawImage(bitmap, 0, y, bitmap.width, thisSliceHeight, 0, 0, bitmap.width, thisSliceHeight);

      const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, OUTPUT_MIME, OUTPUT_QUALITY));
      if (!blob) throw new ChapterSliceError(file.name, `Could not slice page ${i + 1} of ${count}`);

      const pageNumber = String(i + 1).padStart(digits, "0");
      files.push(
        new File([blob], `${baseName}-page-${pageNumber}.jpg`, {
          type: OUTPUT_MIME,
          lastModified: file.lastModified,
        })
      );
    }

    return files;
  } finally {
    bitmap.close();
  }
}

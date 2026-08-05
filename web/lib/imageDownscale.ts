import type { OcrRegion } from "./comics-types";

// Long-edge ceiling for an image sent to OCR. Cloud Vision reads comic
// lettering fine well below the resolution a phone camera or a scan
// produces, and every pixel past this point costs upload time, base64
// payload size, and Vision's own processing time for no accuracy gain.
// Deliberately generous rather than aggressive - small furigana and
// dense manga text are the failure mode a too-small ceiling would cause,
// and that failure is invisible until someone reads a bad result.
export const OCR_MAX_EDGE_PX = 2000;

// JPEG rather than PNG: a comic panel is photographic enough that PNG
// stays large, and at this quality the compression artifacts are well
// below what affects character recognition. Panels don't carry alpha
// that OCR cares about.
const OUTPUT_MIME = "image/jpeg";
const OUTPUT_QUALITY = 0.92;

export type DownscaleResult = {
  /** The file to actually upload - the original itself when no resize
   * was needed, so the common already-small case copies nothing. */
  file: File;
  /** Multiply a bbox from the uploaded image's coordinate space by this
   * to get back to the ORIGINAL image's pixel coordinates. Exactly 1
   * when no resize happened. */
  scale: number;
};

/** Scales OCR bboxes from the downscaled image's coordinate space back
 * into the original image's pixel space.
 *
 * This is not optional bookkeeping: components/comics/PanelWorkspace.tsx
 * positions its region overlay by dividing bbox values by the DISPLAYED
 * original image's naturalWidth/naturalHeight, and app/comics/page.tsx's
 * redraw action sends the ORIGINAL file alongside these same boxes for
 * inpainting. Both would be silently, invisibly misaligned - boxes
 * drawn and art erased in the wrong places - if boxes measured on a
 * downscaled image were handed back as-is.
 *
 * Rounded to whole pixels because bbox is a pixel rect everywhere else
 * in this codebase (engine/comics_ocr.py::_bounding_box returns ints).
 */
export function rescaleRegions(regions: OcrRegion[], scale: number): OcrRegion[] {
  if (scale === 1) return regions;
  return regions.map((region) => ({
    ...region,
    bbox: {
      x: Math.round(region.bbox.x * scale),
      y: Math.round(region.bbox.y * scale),
      width: Math.round(region.bbox.width * scale),
      height: Math.round(region.bbox.height * scale),
    },
  }));
}

/** The resize ratio for an image of the given dimensions, and the size
 * it should become. Ratio is 1 (and dimensions unchanged) when the image
 * already fits under the ceiling - shrinking is the only thing this
 * does, it never upscales a small panel into a blurry big one.
 */
export function targetSize(
  width: number,
  height: number,
  maxEdge: number = OCR_MAX_EDGE_PX
): { width: number; height: number; ratio: number } {
  const longEdge = Math.max(width, height);
  if (longEdge <= maxEdge || longEdge === 0) {
    return { width, height, ratio: 1 };
  }
  const ratio = maxEdge / longEdge;
  return {
    width: Math.round(width * ratio),
    height: Math.round(height * ratio),
    ratio,
  };
}

/** Downscales an image file for OCR upload, returning the file to send
 * and the factor needed to map results back to original coordinates.
 *
 * Returns the untouched original (scale 1) whenever resizing isn't
 * needed OR isn't possible - an unreadable image, a browser without
 * canvas/createImageBitmap, a failed encode. A panel that can't be
 * downscaled must still be OCR-able; this is an optimization, and an
 * optimization that can fail a request outright is a bug, not a feature.
 */
export async function downscaleForOcr(
  file: File,
  maxEdge: number = OCR_MAX_EDGE_PX
): Promise<DownscaleResult> {
  if (typeof createImageBitmap !== "function" || typeof document === "undefined") {
    return { file, scale: 1 };
  }

  let bitmap: ImageBitmap;
  try {
    bitmap = await createImageBitmap(file);
  } catch {
    return { file, scale: 1 };
  }

  try {
    const { width, height, ratio } = targetSize(bitmap.width, bitmap.height, maxEdge);
    if (ratio === 1) return { file, scale: 1 };

    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext("2d");
    if (!ctx) return { file, scale: 1 };
    ctx.drawImage(bitmap, 0, 0, width, height);

    const blob = await new Promise<Blob | null>((resolve) =>
      canvas.toBlob(resolve, OUTPUT_MIME, OUTPUT_QUALITY)
    );
    if (!blob) return { file, scale: 1 };

    // Guard against the pathological case where re-encoding produced a
    // LARGER file than the original (a small, already well-compressed
    // source). Sending the original is strictly better there.
    if (blob.size >= file.size) return { file, scale: 1 };

    const resized = new File([blob], file.name, { type: OUTPUT_MIME });
    // Invert the ratio: results measured on the small image get
    // multiplied back up to the original's pixel space.
    return { file: resized, scale: 1 / ratio };
  } catch {
    return { file, scale: 1 };
  } finally {
    bitmap.close();
  }
}

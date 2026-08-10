import { ChapterSliceError, sliceChapterStrip } from "./chapterSlice";

/** Shared by every place a raw image `File[]` can enter the comics
 * workspace - components/comics/PanelUploader.tsx's drop zone/file/folder
 * inputs, AND app/comics/page.tsx's "Add more" input, which used to call
 * addFiles directly and so skipped chapter-strip slicing entirely: a
 * whole-chapter image added this way went straight in as one unsliced
 * panel, silently reproducing the exact garbled-OCR bug slicing exists to
 * prevent. Anything that can hand this function a File[] gets the same
 * slicing behavior for free, with nowhere left to bypass it from.
 *
 * Every file's dimensions are checked in parallel (Promise.allSettled),
 * not one at a time - the common case is a batch of already-correctly-
 * sized panels, and decoding N of them sequentially would add real, felt
 * latency to an upload that needs no slicing at all. A decode failure on
 * one file is collected into `errors` rather than aborting the batch. */
export async function resolveImageUploads(files: File[]): Promise<{ files: File[]; errors: string[] }> {
  const results = await Promise.allSettled(files.map((file) => sliceChapterStrip(file)));
  const resolved: File[] = [];
  const errors: string[] = [];

  for (let i = 0; i < results.length; i++) {
    const result = results[i];
    if (result.status === "fulfilled") {
      resolved.push(...result.value);
    } else {
      const err = result.reason;
      console.error("Chapter-strip slicing failed", files[i].name, err);
      errors.push(err instanceof ChapterSliceError ? `${err.fileName}: ${err.message}` : `${files[i].name}: couldn't be read`);
    }
  }

  return { files: resolved, errors };
}

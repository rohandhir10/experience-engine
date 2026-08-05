"use client";

import JSZip from "jszip";

const ACCEPTED_EXTENSION_RE = /\.(jpe?g|png|webp)$/i;

export class ZipConversionError extends Error {
  constructor(
    public fileName: string,
    message: string
  ) {
    super(message);
    this.name = "ZipConversionError";
  }
}

function mimeTypeForName(name: string): string {
  if (/\.jpe?g$/i.test(name)) return "image/jpeg";
  if (/\.png$/i.test(name)) return "image/png";
  if (/\.webp$/i.test(name)) return "image/webp";
  return "application/octet-stream";
}

/** True for entries a real webtoon/manga ZIP never contains on purpose -
 * macOS's own resource-fork shadow copies and .DS_Store, which every zip
 * built on a Mac carries whether the creator wants them there or not. */
function isJunkEntry(path: string): boolean {
  const baseName = path.split("/").pop() ?? path;
  return path.startsWith("__MACOSX/") || baseName.startsWith(".");
}

/** Extracts every image from a .zip - the standard hand-off format for
 * webtoon episodes (drawn as one tall canvas, then sliced into dozens of
 * platform-sized images and zipped for delivery - see this module's use
 * in PanelUploader.tsx for the citation). Folder structure inside the
 * zip is flattened to each entry's own file name; final ordering is left
 * to app/comics/page.tsx's existing naturalCompare sort over file names,
 * same as any other batch of dropped images, not decided here. */
export async function zipToImageFiles(zipFile: File): Promise<File[]> {
  let zip: JSZip;
  try {
    // Read as an ArrayBuffer rather than handing the File straight to
    // JSZip - .arrayBuffer() is standard on both browser and Node File/
    // Blob, unlike JSZip's own Blob-vs-Node-buffer detection, which
    // doesn't recognize Node's built-in File the way it does a real
    // browser Blob (only surfaced by testing this under Vitest's Node
    // environment, not by browser testing alone).
    zip = await JSZip.loadAsync(await zipFile.arrayBuffer());
  } catch (err) {
    throw new ZipConversionError(
      zipFile.name,
      err instanceof Error ? err.message : "Could not open this ZIP file"
    );
  }

  const entries = Object.values(zip.files).filter(
    (entry) => !entry.dir && ACCEPTED_EXTENSION_RE.test(entry.name) && !isJunkEntry(entry.name)
  );

  if (!entries.length) {
    throw new ZipConversionError(zipFile.name, "No JPG, PNG, or WebP images found in this ZIP.");
  }

  const files: File[] = [];
  for (const entry of entries) {
    const blob = await entry.async("blob");
    const baseName = entry.name.split("/").pop() ?? entry.name;
    files.push(
      new File([blob], baseName, {
        type: mimeTypeForName(baseName),
        lastModified: zipFile.lastModified,
      })
    );
  }

  return files;
}

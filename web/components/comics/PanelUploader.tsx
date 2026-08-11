"use client";

import { useRef, useState } from "react";
import { resolveImageUploads } from "@/lib/panelUpload";
import { PdfConversionError, pdfToImageFiles } from "@/lib/pdfToImages";
import { ZipConversionError, zipToImageFiles } from "@/lib/zipToImages";

const ACCEPTED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"];

function isPdf(file: File): boolean {
  return file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
}

function isZip(file: File): boolean {
  return (
    file.type === "application/zip" ||
    file.type === "application/x-zip-compressed" ||
    file.name.toLowerCase().endsWith(".zip")
  );
}

/** Drag-and-drop (or file-picker) entry point for a chapter's worth of
 * panel images. Known limitation, stated plainly: dropping a folder onto
 * the page is not read recursively - browsers expose a dropped folder's
 * contents through an async directory-entry API, not as plain File
 * objects, and wiring that up is real additional work. For now, folders
 * are only supported via the "Choose a folder" button below (native
 * `webkitdirectory` file input), and drag-and-drop accepts individual
 * image files (or PDFs) dragged in directly. Both paths land in the same
 * `onFilesSelected` callback.
 *
 * PDFs are converted client-side (lib/pdfToImages.ts, pdf.js) into one
 * PNG per page, and ZIPs (lib/zipToImages.ts, jszip) are extracted into
 * their contained images - the standard hand-off for a sliced webtoon
 * episode, drawn as one tall canvas then chopped into dozens of
 * platform-sized cuts for delivery - before either reaches this
 * callback. The rest of the pipeline (detection, OCR, adaptation) only
 * ever deals in per-panel images and has no PDF- or ZIP-handling step of
 * its own, so both conversions have to happen here, not downstream.
 *
 * A plain image can ALSO be that same unsliced whole-chapter export,
 * dropped in directly instead of pre-cut - a real, unannounced upload
 * shape, not a hypothetical. lib/panelUpload.ts's resolveImageUploads
 * (lib/chapterSlice.ts underneath) checks every accepted image's own
 * dimensions and, past its aspect-ratio/height thresholds, cuts it into
 * page-sized slices right here too - before it ever becomes a "panel"
 * and reaches lib/imageDownscale.ts's OCR shrink, which would otherwise
 * crush a 30,000px-tall strip down to 2000px and make every speech
 * bubble unreadable with no error at all. app/comics/page.tsx's "Add
 * more" input calls the same resolveImageUploads directly (it doesn't
 * render this component) - see that file for why that split existed
 * and had to be closed. */
export function PanelUploader({
  onFilesSelected,
}: {
  onFilesSelected: (files: File[]) => void;
}) {
  const [dragActive, setDragActive] = useState(false);
  const [converting, setConverting] = useState<string | null>(null);
  const [conversionErrors, setConversionErrors] = useState<string[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);

  type Convertible = { kind: "pdf" | "zip"; file: File };

  function splitAcceptable(files: FileList | File[]): { images: File[]; convertibles: Convertible[] } {
    const images: File[] = [];
    const convertibles: Convertible[] = [];
    for (const file of Array.from(files)) {
      if (ACCEPTED_IMAGE_TYPES.includes(file.type)) images.push(file);
      else if (isPdf(file)) convertibles.push({ kind: "pdf", file });
      else if (isZip(file)) convertibles.push({ kind: "zip", file });
    }
    return { images, convertibles };
  }

  async function handleIncoming(files: FileList | File[]) {
    const { images, convertibles } = splitAcceptable(files);
    const errors: string[] = [];

    if (images.length) {
      const resolved = await resolveImageUploads(images);
      errors.push(...resolved.errors);
      if (resolved.files.length) onFilesSelected(resolved.files);
    }

    for (const { kind, file } of convertibles) {
      setConverting(file.name);
      try {
        const extracted =
          kind === "pdf"
            ? await pdfToImageFiles(file, (pageNumber, totalPages) =>
                setConverting(`${file.name} (page ${pageNumber} of ${totalPages})`)
              )
            : await zipToImageFiles(file);
        onFilesSelected(extracted);
      } catch (err) {
        console.error(`${kind.toUpperCase()} conversion failed`, file.name, err);
        const message =
          err instanceof PdfConversionError || err instanceof ZipConversionError
            ? `${err.fileName}: ${err.message}`
            : `${file.name}: couldn't be converted`;
        errors.push(message);
      }
    }
    setConverting(null);
    if (errors.length) setConversionErrors(errors);
  }

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDragActive(true);
      }}
      onDragLeave={() => setDragActive(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragActive(false);
        void handleIncoming(e.dataTransfer.files);
      }}
      className={`relative flex flex-col items-center justify-center gap-4 overflow-hidden rounded-2xl border-2 border-dashed px-8 py-16 text-center transition ${
        dragActive
          ? "border-accent/50 bg-accent/[0.04]"
          : "border-accent/[0.18] bg-black/[0.015] dark:border-white/[0.12] dark:bg-white/[0.02]"
      }`}
    >
      {/* A halftone screentone texture (classic comic-print dot pattern)
          plus two faded, empty speech-bubble outlines - low-opacity enough
          to stay out of the way of the actual copy and buttons, but
          enough to read as an environment meant for comic art specifically
          rather than a generic file-uploader box (real feedback: it
          looked exactly like a PDF converter's dropzone before this). All
          decorative and non-interactive (aria-hidden, pointer-events-none,
          painted first so real content stacks above it), currentColor-
          driven so it follows the accent/theme instead of needing its own
          light/dark pair. */}
      <div aria-hidden="true" className="pointer-events-none absolute inset-0">
        <div
          className="absolute inset-0 text-accent/[0.05] dark:text-white/[0.06]"
          style={{
            backgroundImage: "radial-gradient(currentColor 1px, transparent 1px)",
            backgroundSize: "15px 15px",
          }}
        />
        <BlankSpeechBubble className="absolute -left-7 -top-9 h-28 w-36 -rotate-6 text-accent/[0.07] dark:text-white/[0.05]" />
        <BlankSpeechBubble
          flip
          className="absolute -bottom-10 -right-8 h-32 w-40 rotate-3 text-accent/[0.06] dark:text-white/[0.045]"
        />
      </div>

      {/* Positioned (relative), not static - the decorative texture above
          is absolutely positioned, and per CSS's painting order that
          paints above static in-flow content regardless of DOM order.
          Wrapping the real content in its own positioned box (stack
          level 0, same as the texture) puts DOM order back in charge, so
          this - coming after the texture in markup - paints on top of it
          rather than being silently hidden underneath. */}
      <div className="relative flex flex-col items-center gap-4">
        <p className="text-[15px] font-medium text-ink dark:text-ink-dark">
          Drop chapter images, a PDF, or a ZIP here
        </p>
        <p className="max-w-sm text-[13px] leading-relaxed text-ink/45 dark:text-ink-dark/45">
          JPG, PNG, or WebP panel slices, in any order — they'll be sorted by file name once
          they're in. A PDF works too: each page becomes its own panel automatically. So does a
          ZIP of pre-sliced images — the standard hand-off for a webtoon episode.
        </p>

        {converting && (
          <p className="text-[12px] text-ink/50 dark:text-ink-dark/50">
            Converting {converting}…
          </p>
        )}
        {conversionErrors.length > 0 && (
          <div className="max-w-sm text-[12px] leading-relaxed text-red-600/80 dark:text-red-400/80">
            {conversionErrors.map((error) => (
              <p key={error}>{error}</p>
            ))}
          </div>
        )}

        <div className="flex flex-wrap items-center justify-center gap-3">
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="rounded-full bg-accent px-5 py-2 text-[13px] font-medium text-white transition hover:brightness-110 active:scale-[0.97]"
          >
            Choose files
          </button>
          <button
            type="button"
            onClick={() => folderInputRef.current?.click()}
            className="rounded-full border border-black/[0.1] px-5 py-2 text-[13px] font-medium text-ink/70 transition hover:border-black/20 hover:text-ink dark:border-white/[0.12] dark:text-ink-dark/70 dark:hover:text-ink-dark"
          >
            Choose a folder
          </button>
        </div>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept="image/jpeg,image/png,image/webp,application/pdf,.pdf,application/zip,application/x-zip-compressed,.zip"
        className="hidden"
        onChange={(e) => {
          if (e.target.files) void handleIncoming(e.target.files);
          e.target.value = "";
        }}
      />
      <input
        ref={folderInputRef}
        type="file"
        multiple
        // webkitdirectory is non-standard but supported across every
        // major browser for exactly this "pick a folder" use case.
        // @ts-expect-error - not in the DOM lib's HTMLInputElement type
        webkitdirectory=""
        className="hidden"
        onChange={(e) => {
          if (e.target.files) void handleIncoming(e.target.files);
          e.target.value = "";
        }}
      />
    </div>
  );
}

/** An empty speech-bubble outline (rounded rect + tail), stroke only, no
 * text and no fill besides the surface it's stacked on - decoration for
 * the dropzone texture above, nothing else reads its content, hence
 * aria-hidden at the call site rather than here. */
function BlankSpeechBubble({ className, flip }: { className?: string; flip?: boolean }) {
  return (
    <svg viewBox="0 0 120 84" fill="none" className={className}>
      <rect x="4" y="4" width="112" height="56" rx="18" stroke="currentColor" strokeWidth="3" />
      <path
        d={flip ? "M84 60 L100 80 L70 62 Z" : "M36 60 L20 80 L50 62 Z"}
        stroke="currentColor"
        strokeWidth="3"
        strokeLinejoin="round"
      />
    </svg>
  );
}

"use client";

import { useRef, useState } from "react";

const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp"];

/** Drag-and-drop (or file-picker) entry point for a chapter's worth of
 * panel images. Known limitation, stated plainly: dropping a folder onto
 * the page is not read recursively - browsers expose a dropped folder's
 * contents through an async directory-entry API, not as plain File
 * objects, and wiring that up is real additional work. For now, folders
 * are only supported via the "Choose a folder" button below (native
 * `webkitdirectory` file input), and drag-and-drop accepts individual
 * image files dragged in directly. Both paths land in the same
 * `onFilesSelected` callback. */
export function PanelUploader({
  onFilesSelected,
}: {
  onFilesSelected: (files: File[]) => void;
}) {
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);

  function acceptImages(files: FileList | File[]): File[] {
    return Array.from(files).filter((file) => ACCEPTED_TYPES.includes(file.type));
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
        const files = acceptImages(e.dataTransfer.files);
        if (files.length) onFilesSelected(files);
      }}
      className={`flex flex-col items-center justify-center gap-4 rounded-2xl border-2 border-dashed px-8 py-16 text-center transition ${
        dragActive
          ? "border-accent/50 bg-accent/[0.04]"
          : "border-black/[0.12] dark:border-white/[0.12]"
      }`}
    >
      <p className="text-[15px] font-medium text-ink dark:text-ink-dark">
        Drop chapter images here
      </p>
      <p className="max-w-sm text-[13px] leading-relaxed text-ink/45 dark:text-ink-dark/45">
        JPG, PNG, or WebP panel slices, in any order — they'll be sorted by file name once
        they're in.
      </p>

      <div className="flex flex-wrap items-center justify-center gap-3">
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          className="rounded-full border border-black/[0.1] px-5 py-2 text-[13px] font-medium text-ink/70 transition hover:border-black/20 hover:text-ink dark:border-white/[0.12] dark:text-ink-dark/70 dark:hover:text-ink-dark"
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

      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept="image/jpeg,image/png,image/webp"
        className="hidden"
        onChange={(e) => {
          if (e.target.files) {
            const files = acceptImages(e.target.files);
            if (files.length) onFilesSelected(files);
          }
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
          if (e.target.files) {
            const files = acceptImages(e.target.files);
            if (files.length) onFilesSelected(files);
          }
          e.target.value = "";
        }}
      />
    </div>
  );
}

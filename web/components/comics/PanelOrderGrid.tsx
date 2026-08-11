"use client";

import { useState } from "react";
import type { ComicPanel } from "@/lib/comics-types";

/** A macro overview of every uploaded page, in the order a whole-chapter
 * adaptation will actually process them in - shown once, before the
 * single-panel workspace below it, specifically so a wrong page order
 * (a multi-file upload landing out of sequence, a misnamed file) gets
 * caught before "Adapt chapter" spends real per-panel credits
 * (server/main.py's CREDITS_PER_PANEL) processing pages in the wrong
 * order. Nothing here re-derives order from anything - the numbered
 * badge is exactly this array's index, the same order chapter-level
 * adaptation (lib/comics-types.ts::panelToChapterBubbles, run per
 * `panels` in that order) will use.
 *
 * Reordering has two independent paths to the same lib/comics-
 * types.ts::moveItem call: native HTML5 drag-and-drop for a mouse, and
 * always-visible ‹ › buttons for touch (no hover state to reveal a
 * drag handle) and keyboard/screen-reader use (a real, focusable
 * <button>, not a div with drag handlers only a pointer can reach).
 *
 * Only rendered once there's an actual order worth verifying - a
 * single page has nothing to reorder.
 */
export function PanelOrderGrid({
  panels,
  onReorder,
}: {
  panels: ComicPanel[];
  onReorder: (fromIndex: number, toIndex: number) => void;
}) {
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);

  if (panels.length < 2) return null;

  function handleDrop(index: number) {
    if (dragIndex !== null && dragIndex !== index) {
      onReorder(dragIndex, index);
    }
    setDragIndex(null);
    setDragOverIndex(null);
  }

  return (
    <div className="mt-6">
      <p className="text-[13px] text-ink/65 dark:text-ink-dark/65">
        Page order - drag to fix, or use the arrows, before adapting the chapter.
      </p>
      <div className="mt-3 grid grid-cols-3 gap-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8">
        {panels.map((panel, index) => (
          <div
            key={panel.id}
            draggable
            onDragStart={() => setDragIndex(index)}
            onDragOver={(e) => {
              e.preventDefault();
              if (dragIndex !== null) setDragOverIndex(index);
            }}
            onDragLeave={() => setDragOverIndex((current) => (current === index ? null : current))}
            onDrop={(e) => {
              e.preventDefault();
              handleDrop(index);
            }}
            onDragEnd={() => {
              setDragIndex(null);
              setDragOverIndex(null);
            }}
            className={`group relative cursor-grab overflow-hidden rounded-lg border transition active:cursor-grabbing ${
              dragOverIndex === index && dragIndex !== index
                ? "border-accent"
                : "border-black/[0.12] dark:border-white/[0.12]"
            } ${dragIndex === index ? "opacity-40" : ""}`}
          >
            <span className="absolute left-1.5 top-1.5 z-10 flex h-5 w-5 items-center justify-center rounded-full bg-ink/80 text-[10px] font-medium text-paper dark:bg-black/70">
              {index + 1}
            </span>
            {/* eslint-disable-next-line @next/next/no-img-element -- a
                blob: object URL, next/image's remote-loader path doesn't
                apply and isn't configured for it. */}
            <img
              src={panel.previewUrl}
              alt={`Page ${index + 1}: ${panel.fileName}`}
              className="aspect-[3/4] w-full bg-black/[0.02] object-cover dark:bg-white/[0.02]"
              draggable={false}
            />
            <div className="absolute inset-x-0 bottom-0 flex items-center justify-between bg-gradient-to-t from-black/60 to-transparent px-1 py-1">
              <button
                type="button"
                aria-label={`Move page ${index + 1} earlier`}
                disabled={index === 0}
                onClick={() => onReorder(index, index - 1)}
                className="rounded px-1.5 py-0.5 text-[11px] text-white/90 transition hover:bg-white/20 disabled:cursor-not-allowed disabled:opacity-30"
              >
                ‹
              </button>
              <button
                type="button"
                aria-label={`Move page ${index + 1} later`}
                disabled={index === panels.length - 1}
                onClick={() => onReorder(index, index + 1)}
                className="rounded px-1.5 py-0.5 text-[11px] text-white/90 transition hover:bg-white/20 disabled:cursor-not-allowed disabled:opacity-30"
              >
                ›
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

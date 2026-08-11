"use client";

import { useState } from "react";
import {
  moveItem,
  ocrRerunWouldDiscardWork,
  panelAdaptStatus,
  type ComicPanel,
} from "@/lib/comics-types";
import {
  FONT_OPTIONS,
  resolveRedrawRegionText,
  resolveRedrawRegionTextSource,
} from "@/lib/comicsRedraw";
import { PanelStatusBadge } from "./PanelStatusBadge";

/** Panel-by-panel review: a thumbnail rail to jump between panels, the
 * active panel's real image (with a real OCR pass's bounding boxes
 * overlaid, once run) on one side, and its script fields on the other.
 * "Extracted text"/"Adapted text" stay plain editable fields regardless
 * of whether OCR has run - OCR only ever pre-fills a draft, never locks
 * the field or overwrites something the human already typed.
 *
 * Original/Redrawn toggle: once a panel has a real redraw result, the
 * main image frame shows an Original/Redrawn tab pair instead of two
 * separate stacked images (the original with OCR boxes used to live
 * here, and the redrawn composite lived again further down, after the
 * Redraw button - a real trust-building comparison neither reader could
 * do without scrolling back and forth). One frame, one toggle; the
 * OCR-box overlay only ever applies to the Original tab, since those
 * boxes describe the original image's regions and have no meaning
 * against the redrawn composite. Remembered PER PANEL (imageViewByPanel
 * below), not one shared toggle - switching away from a panel and back
 * shows whatever tab you last had it on, rather than always snapping
 * back to "original" (a real friction point: reviewing a redraw used to
 * mean re-clicking "Redrawn" every time). A panel with no entry yet - a
 * fresh one, or one with no redraw result - defaults to "original".
 *
 * Reading order: Cloud Vision returns detected regions sorted by plain
 * top-to-bottom/left-to-right position (see engine/comics_ocr.py's
 * docstring) - wrong for manga's right-to-left reading, and not
 * guaranteed correct for any multi-bubble panel whose actual reading
 * order isn't simple geometry. The numbered badges below double as a
 * reorder control: the human fixes the order before it ever feeds a
 * chapter-level adaptation pass, the same review step every other
 * ingestion path in this project (YouTube captions, the literal
 * anchor) already requires before trusting machine output.
 *
 * Speaker/voice: a free-text field, not a dropdown tied to a fixed
 * roster - the set of characters isn't known until Chapter DNA runs
 * (and even then a human should be free to name someone it didn't
 * profile). Autocompletes from names already used on other panels
 * (native <datalist>, no extra state or library) so the same character
 * gets typed consistently across a chapter. This is what actually
 * drives per-character voice consistency and honorific-register
 * tracking server-side (engine/comics_adapt.py) - a panel left
 * unattributed still adapts fine, it just doesn't get either benefit. */
export function PanelWorkspace({
  panels,
  onUpdatePanel,
  onRemovePanel,
  onRunOcr,
  onRedrawPanel,
  adapting = false,
}: {
  panels: ComicPanel[];
  onUpdatePanel: (id: string, patch: Partial<ComicPanel>) => void;
  onRemovePanel: (id: string) => void;
  onRunOcr: (id: string) => void;
  onRedrawPanel: (id: string) => void;
  // Whether a whole-chapter "Adapt chapter" job is currently running - see
  // PanelStatusBadge's own docstring for why this gates the spinner state.
  adapting?: boolean;
}) {
  const [activeId, setActiveId] = useState(panels[0]?.id);
  const [naturalSize, setNaturalSize] = useState<{ width: number; height: number } | null>(null);
  // Which image the main frame shows - "original" (with OCR region
  // boxes overlaid) or "redrawn" (the typeset result) - keyed PER PANEL
  // rather than one shared piece of state, so switching away from and
  // back to a panel remembers its own last-viewed tab instead of always
  // snapping back to "original" (a real friction point found auditing
  // this page: reviewing a redraw meant re-clicking "Redrawn" every
  // single time you came back to that panel). A panel with no entry yet
  // defaults to "original" below, same as before this existed - a fresh
  // panel (or one with no redraw result) has nothing meaningful to
  // remember.
  const [imageViewByPanel, setImageViewByPanel] = useState<Record<string, "original" | "redrawn">>(
    {}
  );
  const activeIndex = panels.findIndex((p) => p.id === activeId);
  const active = panels[activeIndex] ?? panels[0];
  const imageView = (active && imageViewByPanel[active.id]) ?? "original";

  if (!active) return null;

  function setImageView(view: "original" | "redrawn") {
    setImageViewByPanel((prev) => ({ ...prev, [active.id]: view }));
  }

  function goTo(index: number) {
    const clamped = Math.max(0, Math.min(panels.length - 1, index));
    setActiveId(panels[clamped].id);
    setNaturalSize(null);
  }

  function moveRegion(fromIndex: number, toIndex: number) {
    const regions = active.ocrRegions;
    if (!regions) return;
    onUpdatePanel(active.id, { ocrRegions: moveItem(regions, fromIndex, toIndex) });
  }

  function applyRegionOrderToExtractedText() {
    if (!active.ocrRegions) return;
    onUpdatePanel(active.id, {
      extractedText: active.ocrRegions.map((r) => r.text).join("\n\n"),
    });
  }

  function setRedrawRegionText(index: number, value: string) {
    const regions = active.ocrRegions;
    if (!regions) return;
    const next = [...(active.redrawRegionTexts ?? new Array(regions.length).fill(null))];
    next[index] = value;
    onUpdatePanel(active.id, { redrawRegionTexts: next });
  }

  function setRedrawRegionFont(index: number, value: string) {
    const regions = active.ocrRegions;
    if (!regions) return;
    const next = [...(active.redrawRegionFonts ?? new Array(regions.length).fill(null))];
    next[index] = value || null;
    onUpdatePanel(active.id, { redrawRegionFonts: next });
  }

  function setRegionAdaptedText(index: number, value: string) {
    const regions = active.ocrRegions;
    if (!regions) return;
    const next = [...(active.regionAdaptedTexts ?? new Array(regions.length).fill(null))];
    next[index] = value;
    onUpdatePanel(active.id, { regionAdaptedTexts: next });
  }

  function setRegionWhy(index: number, value: string) {
    const regions = active.ocrRegions;
    if (!regions) return;
    const next = [...(active.regionWhys ?? new Array(regions.length).fill(null))];
    next[index] = value;
    onUpdatePanel(active.id, { regionWhys: next });
  }

  const knownVoices = Array.from(
    new Set(panels.map((p) => p.voice?.trim()).filter((v): v is string => !!v))
  ).sort((a, b) => a.localeCompare(b));

  return (
    <div className="flex flex-col gap-8 sm:flex-row">
      <div className="flex gap-2 overflow-x-auto pb-2 sm:w-40 sm:shrink-0 sm:flex-col sm:overflow-visible sm:pb-0">
        {panels.map((panel, index) => (
          <button
            key={panel.id}
            type="button"
            onClick={() => {
              setActiveId(panel.id);
              setNaturalSize(null);
            }}
            className={`relative shrink-0 overflow-hidden rounded-lg border transition ${
              panel.id === active.id
                ? "border-accent"
                : "border-black/[0.12] hover:border-black/20 dark:border-white/[0.13]"
            }`}
          >
            <img
              src={panel.previewUrl}
              alt={`Panel ${index + 1}: ${panel.fileName}`}
              className="h-20 w-20 object-cover sm:h-24 sm:w-full"
            />
            <span className="absolute bottom-1 right-1 rounded bg-black/60 px-1.5 py-0.5 text-[10px] text-white">
              {index + 1}
            </span>
            <span className="absolute right-1 top-1">
              <PanelStatusBadge status={panelAdaptStatus(panel)} adapting={adapting} />
            </span>
          </button>
        ))}
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between">
          <p className="text-[12px] uppercase tracking-[0.1em] text-ink/62 dark:text-ink-dark/62">
            Panel {activeIndex + 1} of {panels.length} · {active.fileName}
          </p>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => goTo(activeIndex - 1)}
              disabled={activeIndex === 0}
              className="text-[13px] text-ink/75 transition hover:text-ink disabled:cursor-not-allowed disabled:opacity-30 dark:text-ink-dark/75 dark:hover:text-ink-dark"
            >
              ← Prev
            </button>
            <button
              type="button"
              onClick={() => goTo(activeIndex + 1)}
              disabled={activeIndex === panels.length - 1}
              className="text-[13px] text-ink/75 transition hover:text-ink disabled:cursor-not-allowed disabled:opacity-30 dark:text-ink-dark/75 dark:hover:text-ink-dark"
            >
              Next →
            </button>
            <button
              type="button"
              onClick={() => {
                // Always confirmed, regardless of how much work exists on
                // this panel - this button sits right next to Prev/Next in
                // a tight row, and Remove is instant and has no undo, so a
                // misclick alone is real risk even on a barely-touched
                // panel, not just a heavily-edited one.
                if (window.confirm(`Remove "${active.fileName}"? This can't be undone.`)) {
                  onRemovePanel(active.id);
                }
              }}
              className="text-[13px] text-red-500/70 transition hover:text-red-500"
            >
              Remove
            </button>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-1 gap-6 md:grid-cols-2">
          <div>
            {/* Only shown once there's a second real image to compare
                against - a panel with no redraw result yet has nothing
                to toggle to, so showing an inert "Redrawn" tab would be
                clicking into an empty state rather than a real view. */}
            {active.redrawResultUrl && (
              <div className="mb-2 inline-flex rounded-full border border-black/[0.12] p-0.5 text-[12px] dark:border-white/[0.13]">
                <button
                  type="button"
                  onClick={() => setImageView("original")}
                  className={`rounded-full px-3 py-1 font-medium transition ${
                    imageView === "original"
                      ? "bg-ink text-paper dark:bg-ink-dark dark:text-paper-dark"
                      : "text-ink/68 hover:text-ink dark:text-ink-dark/68 dark:hover:text-ink-dark"
                  }`}
                >
                  Original
                </button>
                <button
                  type="button"
                  onClick={() => setImageView("redrawn")}
                  className={`rounded-full px-3 py-1 font-medium transition ${
                    imageView === "redrawn"
                      ? "bg-ink text-paper dark:bg-ink-dark dark:text-paper-dark"
                      : "text-ink/68 hover:text-ink dark:text-ink-dark/68 dark:hover:text-ink-dark"
                  }`}
                >
                  Redrawn
                </button>
              </div>
            )}
            <div className="relative overflow-hidden rounded-xl border border-black/[0.12] bg-black/[0.02] dark:border-white/[0.12] dark:bg-white/[0.02]">
              {imageView === "redrawn" && active.redrawResultUrl ? (
                // The actual typeset result - no OCR boxes overlaid,
                // since those describe the ORIGINAL image's regions and
                // have no meaning against the redrawn composite.
                <img
                  key={active.redrawResultUrl}
                  src={active.redrawResultUrl}
                  alt={`Redrawn version of ${active.fileName}`}
                  className="w-full"
                />
              ) : (
                <>
                  {/* A real, unmodified render of the user's own file. Boxes
                      are drawn in percentage coordinates (region pixel / the
                      image's own natural size), so they stay aligned with
                      the image regardless of its rendered width. */}
                  <img
                    key={active.id}
                    src={active.previewUrl}
                    alt={active.fileName}
                    className="w-full"
                    onLoad={(e) => {
                      const img = e.currentTarget;
                      setNaturalSize({ width: img.naturalWidth, height: img.naturalHeight });
                    }}
                  />
                  {naturalSize &&
                    active.ocrRegions?.map((region, i) => (
                      <div
                        key={i}
                        title={`${region.text} (${region.confidence.toFixed(0)}% confidence)`}
                        className="absolute border-2 border-accent/70 bg-accent/10"
                        style={{
                          left: `${(region.bbox.x / naturalSize.width) * 100}%`,
                          top: `${(region.bbox.y / naturalSize.height) * 100}%`,
                          width: `${(region.bbox.width / naturalSize.width) * 100}%`,
                          height: `${(region.bbox.height / naturalSize.height) * 100}%`,
                        }}
                      >
                        <span className="absolute -left-2 -top-2 flex h-5 w-5 items-center justify-center rounded-full bg-accent text-[11px] font-medium text-white">
                          {i + 1}
                        </span>
                      </div>
                    ))}
                </>
              )}
            </div>

            <div className="mt-3 flex items-center gap-3">
              <button
                type="button"
                onClick={() => {
                  // Rerunning OCR wipes every region-indexed field (a new
                  // run means new region indices, see ocrRerunWouldDiscardWork's
                  // own docstring) - only worth a confirm when there's
                  // something real to lose, not on the first run.
                  if (
                    ocrRerunWouldDiscardWork(active) &&
                    !window.confirm(
                      "Rerunning OCR clears this panel's detected regions and any adapted text, redraw edits, or redraw result tied to them. Continue?"
                    )
                  ) {
                    return;
                  }
                  onRunOcr(active.id);
                }}
                disabled={active.ocrStatus === "running"}
                className="rounded-full border border-black/[0.13] px-4 py-1.5 text-[13px] font-medium text-ink/78 transition hover:border-black/20 hover:text-ink disabled:cursor-not-allowed disabled:opacity-50 dark:border-white/[0.15] dark:text-ink-dark/78 dark:hover:text-ink-dark"
              >
                {active.ocrStatus === "running"
                  ? "Reading panel…"
                  : active.ocrStatus === "done" || active.ocrStatus === "error"
                    ? "Rerun OCR"
                    : "Run OCR"}
              </button>
              {active.ocrStatus === "done" && !active.ocrMessage && (
                <span className="text-[12px] text-ink/62 dark:text-ink-dark/62">
                  {active.ocrRegions?.length ?? 0} region
                  {(active.ocrRegions?.length ?? 0) === 1 ? "" : "s"} found
                </span>
              )}
            </div>
            {active.ocrMessage && (
              <p
                className={`mt-2 text-[12px] leading-relaxed ${
                  active.ocrStatus === "error" ? "text-red-500/80" : "text-ink/62 dark:text-ink-dark/62"
                }`}
              >
                {active.ocrMessage}
              </p>
            )}

            {active.ocrRegions && active.ocrRegions.length > 1 && (
              <div className="mt-4">
                <p className="text-[13px] font-medium text-ink dark:text-ink-dark">Reading order</p>
                <p className="mt-0.5 text-[11px] text-ink/62 dark:text-ink-dark/62">
                  Vision sorts bubbles top-to-bottom, left-to-right — automatically
                  adjusted right-to-left for Japanese chapters once the language is
                  known, but not guaranteed correct for any multi-bubble panel. Fix the
                  order here before it feeds anything downstream.
                </p>
                <ol className="mt-2 flex flex-col gap-1.5">
                  {active.ocrRegions.map((region, i) => (
                    <li
                      key={i}
                      className="flex items-center gap-2 rounded-lg border border-black/[0.10] bg-white/50 px-2.5 py-1.5 dark:border-white/[0.12] dark:bg-white/[0.02]"
                    >
                      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-accent text-[11px] font-medium text-white">
                        {i + 1}
                      </span>
                      <span className="min-w-0 flex-1 truncate text-[12px] text-ink/72 dark:text-ink-dark/72">
                        {region.text}
                      </span>
                      <button
                        type="button"
                        onClick={() => moveRegion(i, i - 1)}
                        disabled={i === 0}
                        aria-label={`Move region ${i + 1} earlier`}
                        className="shrink-0 text-ink/62 transition hover:text-ink disabled:cursor-not-allowed disabled:opacity-25 dark:text-ink-dark/62 dark:hover:text-ink-dark"
                      >
                        ↑
                      </button>
                      <button
                        type="button"
                        onClick={() => moveRegion(i, i + 1)}
                        disabled={i === active.ocrRegions!.length - 1}
                        aria-label={`Move region ${i + 1} later`}
                        className="shrink-0 text-ink/62 transition hover:text-ink disabled:cursor-not-allowed disabled:opacity-25 dark:text-ink-dark/62 dark:hover:text-ink-dark"
                      >
                        ↓
                      </button>
                    </li>
                  ))}
                </ol>
                <button
                  type="button"
                  onClick={applyRegionOrderToExtractedText}
                  className="mt-2 text-[12px] text-ink/75 underline decoration-ink/15 underline-offset-4 transition hover:text-ink/78 hover:decoration-ink/30 dark:text-ink-dark/75 dark:decoration-ink-dark/15 dark:hover:text-ink-dark/78"
                >
                  Apply this order to Extracted text
                </button>
              </div>
            )}

            {active.ocrRegions && active.ocrRegions.length > 0 && (
              <div className="mt-4">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-[13px] font-medium text-ink dark:text-ink-dark">Redraw</p>
                  <label className="flex items-center gap-1.5">
                    <span className="text-[11px] text-ink/62 dark:text-ink-dark/62">Font</span>
                    <select
                      value={active.redrawFont ?? ""}
                      onChange={(e) => onUpdatePanel(active.id, { redrawFont: e.target.value || null })}
                      className="rounded-md border border-black/[0.12] bg-white/70 px-1.5 py-1 text-[11px] text-ink dark:border-white/[0.12] dark:bg-white/[0.03] dark:text-ink-dark"
                    >
                      {FONT_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
                <p className="mt-0.5 text-[11px] text-ink/62 dark:text-ink-dark/62">
                  Erases the original text out of a bubble and draws the line below back in
                  its place — speech bubbles only, a small set of bundled comic fonts (never
                  an exact match for the original lettering), a best-guess text color. Only
                  regions with text below get redrawn; leave one blank to skip it. Each
                  region can override the panel's default font above.
                </p>
                <ol className="mt-2 flex flex-col gap-2">
                  {active.ocrRegions.map((region, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="mt-2 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-accent text-[11px] font-medium text-white">
                        {i + 1}
                      </span>
                      <div className="min-w-0 flex-1">
                        {/* Which of resolveRedrawRegionText's three
                            sources actually filled this box - a real gap
                            this closes: editing this text, then rerunning
                            OCR, used to silently repopulate it from a
                            DIFFERENT source with no visible sign anything
                            changed (see resolveRedrawRegionTextSource's
                            own docstring). */}
                        <p className="mb-0.5 text-[10px] text-ink/50 dark:text-ink-dark/50">
                          {resolveRedrawRegionTextSource(active, i) === "override"
                            ? "Your own edit"
                            : resolveRedrawRegionTextSource(active, i) === "adaptation"
                              ? "From the chapter adaptation"
                              : "Nothing here yet — type this bubble's line to redraw it"}
                        </p>
                        <textarea
                          value={resolveRedrawRegionText(active, i)}
                          onChange={(e) => setRedrawRegionText(i, e.target.value)}
                          rows={2}
                          placeholder={`Adapted text for region ${i + 1}…`}
                          className="w-full resize-none rounded-lg border border-black/[0.12] bg-white/70 px-2.5 py-1.5 text-[13px] leading-snug text-ink placeholder:text-ink/45 transition dark:border-white/[0.12] dark:bg-white/[0.03] dark:text-ink-dark dark:placeholder:text-ink-dark/45"
                        />
                        <select
                          value={active.redrawRegionFonts?.[i] ?? ""}
                          onChange={(e) => setRedrawRegionFont(i, e.target.value)}
                          className="mt-1 rounded-md border border-black/[0.12] bg-white/70 px-1.5 py-0.5 text-[11px] text-ink/72 dark:border-white/[0.12] dark:bg-white/[0.03] dark:text-ink-dark/72"
                        >
                          <option value="">Use panel default</option>
                          {FONT_OPTIONS.map((opt) => (
                            <option key={opt.value} value={opt.value}>
                              {opt.label}
                            </option>
                          ))}
                        </select>
                      </div>
                    </li>
                  ))}
                </ol>
                <div className="mt-3 flex items-center gap-3">
                  <button
                    type="button"
                    onClick={() => onRedrawPanel(active.id)}
                    disabled={active.redrawStatus === "running"}
                    className="rounded-full border border-black/[0.13] px-4 py-1.5 text-[13px] font-medium text-ink/78 transition hover:border-black/20 hover:text-ink disabled:cursor-not-allowed disabled:opacity-50 dark:border-white/[0.15] dark:text-ink-dark/78 dark:hover:text-ink-dark"
                  >
                    {active.redrawStatus === "running" ? "Redrawing…" : "Redraw panel"}
                  </button>
                  {active.redrawResultUrl && (
                    <a
                      href={active.redrawResultUrl}
                      download={`redrawn-${active.fileName}`}
                      className="text-[12px] text-ink/75 underline decoration-ink/15 underline-offset-4 transition hover:text-ink/78 hover:decoration-ink/30 dark:text-ink-dark/75 dark:decoration-ink-dark/15 dark:hover:text-ink-dark/78"
                    >
                      Download result
                    </a>
                  )}
                </div>
                {active.redrawMessage && (
                  <p
                    className={`mt-2 text-[12px] leading-relaxed ${
                      active.redrawStatus === "error" ? "text-red-500/80" : "text-ink/62 dark:text-ink-dark/62"
                    }`}
                  >
                    {active.redrawMessage}
                  </p>
                )}
                {/* The result itself now shows in the main image frame
                    above (the Original/Redrawn toggle), not duplicated
                    here a second time - "Download result" above is
                    still the real, separate action of saving the file. */}
              </div>
            )}
          </div>

          <div className="flex flex-col gap-4">
            <label className="block">
              <span className="text-[13px] font-medium text-ink dark:text-ink-dark">
                Speaker
              </span>
              <p className="mt-0.5 text-[11px] text-ink/62 dark:text-ink-dark/62">
                Who's talking in this panel — drives voice consistency and honorific tracking
                during adaptation. Leave blank if unattributed (narration, unclear speaker).
              </p>
              <input
                type="text"
                list="comics-known-voices"
                value={active.voice ?? ""}
                onChange={(e) => onUpdatePanel(active.id, { voice: e.target.value || null })}
                placeholder="e.g. Guard Captain"
                className="mt-1.5 w-full rounded-lg border border-black/[0.12] bg-white/70 px-3 py-2 text-[14px] text-ink placeholder:text-ink/45 transition dark:border-white/[0.12] dark:bg-white/[0.03] dark:text-ink-dark dark:placeholder:text-ink-dark/45"
              />
              <datalist id="comics-known-voices">
                {knownVoices.map((voice) => (
                  <option key={voice} value={voice} />
                ))}
              </datalist>
            </label>
            <Field
              label="Extracted text"
              hint="Run OCR to pre-fill this, or type/paste the panel's dialogue by hand."
              value={active.extractedText}
              onChange={(value) => onUpdatePanel(active.id, { extractedText: value })}
            />
            {active.ocrRegions && active.ocrRegions.length > 0 ? (
              <div>
                <span className="text-[13px] font-medium text-ink dark:text-ink-dark">
                  Adapted text, per bubble
                </span>
                <p className="mt-0.5 text-[11px] text-ink/62 dark:text-ink-dark/62">
                  Each detected bubble is adapted on its own — a panel with two speakers
                  gets two independent rewrites, not one block credited to whoever's line
                  came first.
                </p>
                <ol className="mt-2 flex flex-col gap-3">
                  {active.ocrRegions.map((region, i) => (
                    <li
                      key={i}
                      className="rounded-lg border border-black/[0.10] p-2.5 dark:border-white/[0.12]"
                    >
                      <div className="flex items-center gap-2">
                        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-accent text-[11px] font-medium text-white">
                          {i + 1}
                        </span>
                        {region.speaker && (
                          <span className="text-[11px] text-ink/62 dark:text-ink-dark/62">
                            {region.speaker}
                          </span>
                        )}
                      </div>
                      <textarea
                        value={active.regionAdaptedTexts?.[i] ?? ""}
                        onChange={(e) => setRegionAdaptedText(i, e.target.value)}
                        rows={2}
                        placeholder="Adapted text for this bubble…"
                        className="mt-1.5 w-full resize-none rounded-lg border border-black/[0.12] bg-white/70 px-2.5 py-1.5 text-[13px] leading-snug text-ink placeholder:text-ink/45 transition dark:border-white/[0.12] dark:bg-white/[0.03] dark:text-ink-dark dark:placeholder:text-ink-dark/45"
                      />
                      <textarea
                        value={active.regionWhys?.[i] ?? ""}
                        onChange={(e) => setRegionWhy(i, e.target.value)}
                        rows={1}
                        placeholder="Why (optional)…"
                        className="mt-1.5 w-full resize-none rounded-lg border border-black/[0.12] bg-white/70 px-2.5 py-1.5 text-[12px] leading-snug text-ink/72 placeholder:text-ink/45 transition dark:border-white/[0.12] dark:bg-white/[0.03] dark:text-ink-dark/72 dark:placeholder:text-ink-dark/45"
                      />
                    </li>
                  ))}
                </ol>
              </div>
            ) : (
              <>
                <Field
                  label="Adapted text"
                  hint="The rewritten line for this panel."
                  value={active.adaptedText}
                  onChange={(value) => onUpdatePanel(active.id, { adaptedText: value })}
                />
                <Field
                  label="Why"
                  hint="A plain-language reason for anything that changed."
                  value={active.why}
                  onChange={(value) => onUpdatePanel(active.id, { why: value })}
                  rows={2}
                />
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function Field({
  label,
  hint,
  value,
  onChange,
  rows = 3,
}: {
  label: string;
  hint: string;
  value: string;
  onChange: (value: string) => void;
  rows?: number;
}) {
  return (
    <label className="block">
      <span className="text-[13px] font-medium text-ink dark:text-ink-dark">{label}</span>
      <p className="mt-0.5 text-[11px] text-ink/62 dark:text-ink-dark/62">{hint}</p>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={rows}
        className="mt-1.5 w-full resize-none rounded-lg border border-black/[0.12] bg-white/70 px-3 py-2 text-[14px] leading-relaxed text-ink placeholder:text-ink/45 transition dark:border-white/[0.12] dark:bg-white/[0.03] dark:text-ink-dark dark:placeholder:text-ink-dark/45"
      />
    </label>
  );
}

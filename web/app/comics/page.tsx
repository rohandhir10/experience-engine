"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import Link from "next/link";
import { SiteHeader } from "@/components/SiteHeader";
import { CopyLinkButton } from "@/components/CopyLinkButton";
import { TargetLanguageSelect } from "@/components/TargetLanguageSelect";
import { PanelUploader } from "@/components/comics/PanelUploader";
import { PanelWorkspace } from "@/components/comics/PanelWorkspace";
import { PanelOrderGrid } from "@/components/comics/PanelOrderGrid";
import { naturalCompare } from "@/lib/naturalSort";
import { LANGUAGES } from "@/lib/languages";
import {
  applyBubbleResult,
  MAX_COMICS_PANELS_HINT,
  moveItem,
  panelToChapterBubbles,
  panelsToCsv,
  type ComicPanel,
} from "@/lib/comics-types";
import { OcrRequestError, resolvePanelSpeaker, runPanelOcr } from "@/lib/comicsOcr";
import { resolveImageUploads } from "@/lib/panelUpload";
import { OCR_BATCH_CONCURRENCY, runWithConcurrency } from "@/lib/concurrency";
import { guessChapterLanguage } from "@/lib/chapterLanguage";
import { AdaptRequestError, adaptChapter } from "@/lib/comicsAdapt";
import { RedrawRequestError, redrawPanel, resolveRedrawRegionText } from "@/lib/comicsRedraw";
import { writeMediumPreference } from "@/lib/mediumPreference";
import { PanelPipelineStoryboard } from "@/components/comics/PanelPipelineStoryboard";
import { Footer } from "@/components/Footer";
import { ScrollReveal } from "@/components/ScrollReveal";
import { FOUNDER_NAME } from "@/lib/seo";
import { comicsFaqs } from "@/lib/faqs";

// Hand-bumped alongside a real content edit to this page's empty state -
// never build-time. Matches app/page.tsx's PAGE_UPDATED_DATE and
// InputScreen.tsx's own copy of the same convention; this page has its
// own constant since its content changes on its own schedule.
const PAGE_UPDATED_DATE = "2026-08-11";

const COMICS_FAQS = comicsFaqs();

// Now linked from "/" (the Webtoons tile on the medium-chooser split
// screen), rather than reachable only by URL - it earned that entry
// point once OCR + a real adapt call both existed, per the project's
// non-fabrication discipline. Save/collections/share-link DO now work
// the same way they do for music (results are recorded to the same
// adaptations history with medium="webtoons", RecentAdaptations links
// per-medium, and this page's CopyLinkButton below is real). The
// "Beta" badge that used to sit next to the h1 below is gone (real
// feedback that it read as clutter across the nav/tiles/sidebar) - the
// gaps it disclosed are still real and still stated in prose on
// /manga-webtoon-translation and in this page's own meta description
// (app/comics/layout.tsx), just not flagged with a badge here: SFX
// text over textured artwork isn't redrawn (speech bubbles only, see
// engine/comics_redraw.py), OCR reading order is a plain top-to-bottom
// guess unless a text detector service is configured, and cross-
// chapter character memory (the Series field below) matches
// characters by exact name only, not visually.
// "Adapt chapter" runs via
// /api/comics/adapt/start + jobs/[jobId] (lib/comicsAdapt.ts) - the
// same background-job/poll pattern music's /api/adapt/start already
// used, extended here so a large chapter can't hit a request timeout,
// with incremental per-panel progress: the workspace stays unlocked and
// fills in each panel's real adapted text as soon as it's ready, rather
// than sitting on one spinner for however long the whole chapter takes.
// This page is that tool's functional foundation: file upload, a
// panel-by-panel review workspace, a real (if imperfect) OCR pass per
// panel (/api/comics/ocr), and a real adaptation call
// (engine/chapter_dna.py + engine/comics_adapt.py). Each detected OCR
// REGION is its own adaptation unit (lib/comics-types.ts::panelToChapterBubbles),
// not the whole panel flattened into one block - a panel with two
// speakers gets two independent rewrites, each keyed back to its own
// bubble by lib/comics-types.ts::applyBubbleResult. A panel with no
// detected regions (hand-typed dialogue) still adapts as one unit, since
// there's no per-bubble structure to split against.
export default function ComicsPage() {
  const { data: session } = useSession();
  // Persistent character bibles (server/character_bibles.py) need a real
  // owner - server/main.py silently ignores series_name for an anonymous
  // request, so the input is only shown once signed in rather than
  // offering something that would quietly do nothing.
  const signedIn = Boolean(session?.castiaUserId);
  const [panels, setPanels] = useState<ComicPanel[]>([]);
  const [sourceLanguage, setSourceLanguage] = useState("English");
  const [sourceLanguageTouched, setSourceLanguageTouched] = useState(false);
  const [targetLanguage, setTargetLanguage] = useState("English");
  // Ties this chapter's characters to any earlier chapter's saved voice/
  // honorific data for a series of this name under this account
  // (engine/comics_adapt.py::merge_character_bible). Blank means no
  // cross-chapter character memory, same as before this field existed.
  const [seriesName, setSeriesName] = useState("");
  const [batchOcrRunning, setBatchOcrRunning] = useState(false);
  const [adaptStatus, setAdaptStatus] = useState<"idle" | "running" | "error">("idle");
  const [adaptError, setAdaptError] = useState<string | null>(null);
  // Real, incremental status from the background job (server/jobs.py's
  // progress_json) while adaptStatus === "running" - null before the
  // first poll reports anything and once the job settles. Never a
  // fabricated "Analyzing tone…" style message; see comicsAdapt.ts's
  // ChapterAdaptProgress and server/main.py::_run_comics_adaptation for
  // what's actually being reported.
  const [adaptProgress, setAdaptProgress] = useState<{ completed: number; total: number; message: string } | null>(
    null
  );
  // Set once a "Adapt chapter" call succeeds - server/main.py now persists
  // the result under this id (cache.comics_content_id), so it's real and
  // shareable, not a local-only id. Cleared on the next edit that would
  // make the persisted result stale (a panel added/removed, or another
  // adapt run), same "don't imply a link still matches what's on screen"
  // reasoning /s/[id] never has to think about since songs are read-only
  // once shared.
  const [lastAdaptedId, setLastAdaptedId] = useState<string | null>(null);
  // Surfaces a chapter-strip slicing failure from the "Add more" input
  // specifically (lib/panelUpload.ts::resolveImageUploads) - the initial
  // upload's PanelUploader.tsx has its own conversionErrors UI for this
  // same failure; "Add more" doesn't render that component, so it needs
  // its own small surface rather than swallowing the error.
  const [addMoreError, setAddMoreError] = useState<string | null>(null);

  // Written on every real arrival here - see app/music/page.tsx's
  // matching effect for why (tile click, switcher, or a direct URL all
  // count, so "/"'s read/redirect reflects reality, not just clicks
  // that went through the chooser).
  useEffect(() => {
    writeMediumPreference("webtoons");
  }, []);

  function addFiles(files: File[]) {
    const newPanels: ComicPanel[] = files
      .map((file) => ({
        id: `${file.name}-${file.size}-${file.lastModified}`,
        fileName: file.name,
        file,
        previewUrl: URL.createObjectURL(file),
        extractedText: "",
        adaptedText: "",
        why: "",
        ocrStatus: "idle" as const,
        ocrRegions: null,
        ocrMessage: null,
        detectedLanguages: null,
        voice: null,
        regionAdaptedTexts: null,
        regionWhys: null,
        redrawRegionTexts: null,
        redrawFont: null,
        redrawRegionFonts: null,
        redrawResultUrl: null,
        redrawResultId: null,
        redrawStatus: "idle" as const,
        redrawMessage: null,
      }))
      .sort((a, b) => naturalCompare(a.fileName, b.fileName));

    setPanels((prev) => {
      const existingIds = new Set(prev.map((p) => p.id));
      const merged = [...prev, ...newPanels.filter((p) => !existingIds.has(p.id))];
      return merged.sort((a, b) => naturalCompare(a.fileName, b.fileName));
    });
    setLastAdaptedId(null);
  }

  // "Add more"'s own entry point - NOT allowed to call addFiles directly
  // with the raw FileList the way it used to. Routes through the same
  // resolveImageUploads every other upload path uses (PanelUploader.tsx's
  // drop zone/file/folder inputs) so a whole-chapter strip added here
  // gets sliced into pages exactly like one added on the very first
  // upload, instead of silently landing as one unreadable panel.
  async function addMoreFiles(files: File[]) {
    setAddMoreError(null);
    const { files: resolved, errors } = await resolveImageUploads(files);
    if (resolved.length) addFiles(resolved);
    if (errors.length) setAddMoreError(errors.join(" "));
  }

  function updatePanel(id: string, patch: Partial<ComicPanel>) {
    setPanels((prev) => prev.map((p) => (p.id === id ? { ...p, ...patch } : p)));
  }

  async function runOcr(id: string) {
    const panel = panels.find((p) => p.id === id);
    if (!panel) return;
    await ocrPanel(panel);
  }

  // Takes the panel itself rather than looking it up by id, so a batch
  // run works off the panels it captured when the user pressed the
  // button instead of re-reading a `panels` array that its own earlier
  // iterations have already changed. Every write below goes through
  // updatePanel's functional setState, so concurrent panels updating at
  // once can't clobber each other.
  async function ocrPanel(panel: ComicPanel) {
    const id = panel.id;
    updatePanel(id, {
      ocrStatus: "running",
      ocrMessage: null,
      ocrRegions: null,
      // A new OCR run means new region indices - any per-region state
      // tied to the old ones (adaptation results, redraw text, a
      // composited result image) no longer corresponds to anything real.
      regionAdaptedTexts: null,
      regionWhys: null,
      redrawRegionTexts: null,
      redrawRegionFonts: null,
      redrawResultUrl: null,
      redrawResultId: null,
      redrawStatus: "idle",
      redrawMessage: null,
    });
    try {
      const result = await runPanelOcr(panel.file);
      updatePanel(id, {
        ocrStatus: "done",
        ocrRegions: result.regions,
        ocrMessage: result.warning,
        detectedLanguages: result.detectedLanguages,
        // Only pre-fills an empty field - never overwrites text the
        // human has already reviewed/edited by hand.
        extractedText: panel.extractedText.trim() ? panel.extractedText : result.fullText,
        // Same rule for the speaker. Only set when the optional vision
        // pass named exactly one speaker for this panel (see
        // resolvePanelSpeaker) - otherwise it stays whatever it was,
        // including blank.
        voice: panel.voice?.trim()
          ? panel.voice
          : resolvePanelSpeaker(result.regions) ?? panel.voice,
      });
    } catch (err) {
      updatePanel(id, {
        ocrStatus: "error",
        ocrMessage:
          err instanceof OcrRequestError ? err.message : "OCR failed for this panel.",
      });
    }
  }

  // Runs OCR across the whole chapter a few panels at a time. Targets
  // only panels that don't already have a result - re-reading a panel
  // that's already done costs a real, metered Cloud Vision call and
  // would throw away OCR text the human may have started editing. Use
  // the per-panel "Run OCR" button to deliberately redo one.
  async function runOcrForAllPanels() {
    if (batchOcrRunning) return;
    const pending = panels.filter(
      (p) => p.ocrStatus === "idle" || p.ocrStatus === "error"
    );
    if (!pending.length) return;

    setBatchOcrRunning(true);
    try {
      await runWithConcurrency(pending, OCR_BATCH_CONCURRENCY, (panel) => ocrPanel(panel));
    } finally {
      setBatchOcrRunning(false);
    }
  }

  async function redrawPanelAction(id: string) {
    const panel = panels.find((p) => p.id === id);
    if (!panel?.ocrRegions?.length || panel.redrawStatus === "running") return;

    const regionsToSend = panel.ocrRegions
      .map((region, i) => ({
        bbox: region.bbox,
        adaptedText: resolveRedrawRegionText(panel, i).trim(),
        font: panel.redrawRegionFonts?.[i] ?? undefined,
      }))
      .filter((r) => r.adaptedText);

    if (!regionsToSend.length) {
      updatePanel(id, {
        redrawStatus: "error",
        redrawMessage: "Fill in at least one region's adapted text first.",
      });
      return;
    }

    updatePanel(id, { redrawStatus: "running", redrawMessage: null });
    try {
      const { dataUrl, id: redrawResultId } = await redrawPanel(
        panel.file,
        regionsToSend,
        panel.redrawFont ?? undefined
      );
      updatePanel(id, {
        redrawStatus: "idle",
        redrawResultUrl: dataUrl,
        redrawResultId,
        redrawMessage: null,
      });
    } catch (err) {
      updatePanel(id, {
        redrawStatus: "error",
        redrawMessage:
          err instanceof RedrawRequestError ? err.message : "Redrawing this panel failed.",
      });
    }
  }

  function removePanel(id: string) {
    setPanels((prev) => {
      const target = prev.find((p) => p.id === id);
      if (target) URL.revokeObjectURL(target.previewUrl);
      return prev.filter((p) => p.id !== id);
    });
    setLastAdaptedId(null);
  }

  // The order `panels` is in is exactly the order a whole-chapter
  // adaptation processes pages in (adaptWholeChapter below runs
  // panelToChapterBubbles over `panels` as given) - reordering here is
  // reordering the real thing, not a separate "view order" that would
  // need reconciling with it later.
  function reorderPanels(fromIndex: number, toIndex: number) {
    setPanels((prev) => moveItem(prev, fromIndex, toIndex));
  }

  const chapterLanguage = guessChapterLanguage(panels);

  // Pre-fills "From" with Cloud Vision's own guess once it's available
  // and recognized (CASTIA only adapts its 6-language roster today, even
  // though Vision itself can detect more) - same "auto-detect until the
  // human touches it" rule InputScreen.tsx already uses for a pasted
  // song's source language.
  useEffect(() => {
    if (
      !sourceLanguageTouched &&
      chapterLanguage?.languageName &&
      (LANGUAGES as readonly string[]).includes(chapterLanguage.languageName)
    ) {
      setSourceLanguage(chapterLanguage.languageName);
    }
  }, [chapterLanguage?.languageName, sourceLanguageTouched]);

  // Applies one bubble's real adapted result - called both incrementally,
  // as each bubble finishes while the rest of a large chapter is still
  // running (adaptChapter's onProgress below), and once more for the
  // final settled result. A "bubble" is one detected region within a
  // panel when the panel has any (lib/comics-types.ts::panelToChapterBubbles),
  // so this can update just ONE region of a multi-speaker panel without
  // touching the others - the actual fix for panels with more than one
  // speech bubble, which used to be flattened into a single adapted
  // block regardless of how many people were talking.
  //
  // Reads/writes against the functional setPanels updater's own `prev`,
  // not the outer `panels` closure - this runs across a job that can
  // take minutes, during which the human may have already edited a
  // bubble by hand while the rest of the chapter is still adapting (the
  // whole point of not locking the workspace), so the "only pre-fill if
  // still empty" check has to see the LATEST state at the moment each
  // result actually arrives, not a stale snapshot from whenever the
  // button was first clicked.
  function applyPanelResult(bubbleResult: { id: string; adaptedText: string; why: string }) {
    setPanels((prev) => prev.map((panel) => applyBubbleResult(panel, bubbleResult.id, bubbleResult)));
  }

  async function adaptWholeChapter() {
    const bubbles = panels.flatMap(panelToChapterBubbles);
    if (!bubbles.length || adaptStatus === "running") return;
    setAdaptStatus("running");
    setAdaptError(null);
    setAdaptProgress(null);
    try {
      const result = await adaptChapter(
        bubbles,
        sourceLanguage,
        targetLanguage,
        (progress) => {
          setAdaptProgress({ completed: progress.completed, total: progress.total, message: progress.message });
          for (const panelResult of progress.panels) applyPanelResult(panelResult);
        },
        signedIn ? seriesName : undefined
      );
      for (const panelResult of result.panels) applyPanelResult(panelResult);
      setAdaptStatus("idle");
      setAdaptProgress(null);
      setLastAdaptedId(result.id || null);
    } catch (err) {
      setAdaptStatus("error");
      setAdaptProgress(null);
      setAdaptError(
        err instanceof AdaptRequestError ? err.message : "Adapting this chapter failed."
      );
    }
  }

  function exportCsv() {
    const blob = new Blob([panelsToCsv(panels)], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "castia-comics-script.csv";
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <main className="min-h-screen px-6 pb-28 pt-8 sm:px-10">
      <div className="mx-auto max-w-5xl">
        <SiteHeader active="webtoons" />

        <div className="mt-10">
          {panels.length === 0 && (
            <div>
              {/* Single column, not the old two-column [hero | pipeline]
                  grid: that pairing left the hero column tall and dense
                  while the wide-but-short pipeline card left a large,
                  unbalanced pocket of empty space beneath it (real
                  feedback, not a hypothetical). The dropzone - the actual
                  primary action on this page - stays glued directly under
                  the headline instead of being pulled out to its own
                  full-width row, and the pipeline explainer becomes its
                  own full-width band below instead, where it has room to
                  breathe (and for its per-step art - see
                  PanelPipelineStoryboard.tsx). Centered (mx-auto), not
                  left-hugging the wide max-w-5xl
                  shell - a narrower reading measure left un-centered just
                  moved the empty space instead of removing it, all of it
                  landing on the right (real feedback, not a hypothetical -
                  the pipeline band below stays full-width since it isn't
                  a reading-measure block). */}
              <div className="mx-auto max-w-xl">
                <h1 className="font-serif text-2xl text-ink dark:text-ink-dark sm:text-[1.9rem]">
                  Give every character their own voice.
                </h1>
                {/* Short and human, not the old single run-on sentence
                    justifying itself - real feedback that the hero read
                    as descriptive/salesy. The dropped mechanism detail
                    (speech-bubble OCR, per-character voice consistency,
                    the shared Writers' Room pipeline) isn't gone from the
                    page: it's one scroll down in the "What happens to a
                    panel" storyboard, and this layout's own meta
                    description (app/comics/layout.tsx) already carries
                    the fuller version for search results and AI-generated
                    summaries - that was always the structural source for
                    that job, not this paragraph. text-ink/80, not the
                    original /50 - that read as low-contrast on the actual
                    value proposition, not just "editorial." */}
                <p className="mt-3 max-w-md text-[14px] leading-relaxed text-ink/80 dark:text-ink-dark/72">
                  Upload your chapter, and every character keeps their
                  voice — panel after panel.
                </p>
                {/* A real byline (linking to the one page with a real
                    Person bio) plus a real, hand-bumped edit date - see
                    PAGE_UPDATED_DATE above. No photo: none exists, and a
                    stock/generated one would be a fabricated credential. */}
                <p className="mt-2 text-[11.5px] text-ink/68 dark:text-ink-dark/68">
                  Built by{" "}
                  <Link href="/about" className="underline decoration-ink/15 underline-offset-4 hover:text-ink/72 dark:decoration-ink-dark/15 dark:hover:text-ink-dark/72">
                    {FOUNDER_NAME}
                  </Link>
                  {" · "}Updated{" "}
                  <time dateTime={PAGE_UPDATED_DATE}>
                    {new Date(PAGE_UPDATED_DATE + "T00:00:00Z").toLocaleDateString("en-US", {
                      month: "long",
                      day: "numeric",
                      year: "numeric",
                      timeZone: "UTC",
                    })}
                  </time>
                </p>
                <div className="mt-5">
                  <PanelUploader onFilesSelected={addFiles} />
                </div>
              </div>

              {/* A visual storyboard, not five identical text rows in a
                  bordered box - real feedback, not a hypothetical: the
                  old version read like a terms-of-service list, not a
                  product page. Each step now carries its own honest
                  illustration (PanelPipelineStoryboard.tsx's own doc
                  comment covers why these are diagrams, not fabricated
                  screenshots), so the outer wrapper card that used to
                  hold ComicsPipelineDiagram's five plain rows is gone
                  too - five already-bordered storyboard cards inside
                  another bordered card just doubled the chrome. */}
              <div className="mt-14">
                <p className="flex items-center gap-2 text-[12px] uppercase tracking-[0.15em] text-accent dark:text-ink-dark/65">
                  <span className="h-1.5 w-1.5 rounded-full bg-accent dark:bg-ink-dark/30" aria-hidden="true" />
                  What happens to a panel
                </p>
                <div className="mt-5">
                  <PanelPipelineStoryboard />
                </div>
              </div>
            </div>
          )}

          {panels.length === 0 && (
            <ScrollReveal className="mx-auto mt-16 w-full max-w-2xl text-center">
              <p className="flex items-center justify-center gap-2 text-[12px] uppercase tracking-[0.15em] text-accent dark:text-ink-dark/65">
                <span className="h-1.5 w-1.5 rounded-full bg-accent dark:bg-ink-dark/30" aria-hidden="true" />
                Six languages, any direction
              </p>
              <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
                {LANGUAGES.map((lang) => (
                  <span
                    key={lang}
                    className="rounded-full border border-accent/20 px-3 py-1 text-[13px] text-ink/72 dark:border-white/10 dark:text-ink-dark/72"
                  >
                    {lang}
                  </span>
                ))}
              </div>
            </ScrollReveal>
          )}

          {/* Only shown before any real work has started - same
              reasoning PanelOrderGrid.tsx already uses ("nothing here
              worth showing once there's real state to show instead").
              Once panels exist the workspace itself is the content;
              this marketing/reference material would just be in the way. */}
          {panels.length === 0 && (
            <ScrollReveal className="mx-auto mt-20 w-full max-w-2xl border-t border-black/[0.10] pt-16 dark:border-white/[0.10]">
              <div className="mx-auto h-[2px] w-8 rounded-full bg-accent/50" aria-hidden="true" />
              <h2 className="mt-4 text-center font-serif text-[1.6rem] leading-[1.25] text-ink dark:text-ink-dark sm:text-[1.9rem]">
                Common questions
              </h2>
              <div className="mt-8 space-y-6">
                {COMICS_FAQS.map((faq) => (
                  <div key={faq.question} className="border-b border-black/[0.10] pb-6 dark:border-white/[0.11]">
                    <h3 className="font-serif text-[15px] text-ink dark:text-ink-dark">{faq.question}</h3>
                    <p className="mt-2 text-[13px] leading-relaxed text-ink/78 dark:text-ink-dark/78">{faq.answer}</p>
                  </div>
                ))}
              </div>
              <p className="mt-6 text-center text-[13px] text-ink/75 dark:text-ink-dark/75">
                <Link href="/faq" className="underline decoration-ink/20 underline-offset-4 hover:text-ink/78 dark:decoration-ink-dark/20 dark:hover:text-ink-dark/78">
                  See all FAQs
                </Link>
                {" · "}
                <Link href="/pricing" className="underline decoration-ink/20 underline-offset-4 hover:text-ink/78 dark:decoration-ink-dark/20 dark:hover:text-ink-dark/78">
                  See pricing
                </Link>
              </p>
            </ScrollReveal>
          )}

          {panels.length > 0 && (
            <>
              <div className="mt-8 flex flex-wrap items-center justify-between gap-3">
                <div className="flex flex-wrap items-center gap-3">
                  <p className="text-[13px] text-ink/75 dark:text-ink-dark/75">
                    {panels.length} panel{panels.length === 1 ? "" : "s"} loaded
                  </p>
                  {chapterLanguage && (
                    <span className="rounded-full border border-black/[0.12] px-3 py-1 text-[12px] text-ink/68 dark:border-white/[0.12] dark:text-ink-dark/68">
                      Detected language: {chapterLanguage.languageName ?? chapterLanguage.languageCode}
                      {chapterLanguage.ocrdPanelCount > 1 &&
                        ` (${chapterLanguage.agreeingPanelCount} of ${chapterLanguage.ocrdPanelCount} OCR'd panels)`}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-4">
                  <label className="cursor-pointer text-[13px] text-ink/75 underline decoration-ink/15 underline-offset-4 transition hover:text-ink/78 hover:decoration-ink/30 dark:text-ink-dark/75 dark:decoration-ink-dark/15 dark:hover:text-ink-dark/78">
                    Add more
                    <input
                      type="file"
                      multiple
                      accept="image/jpeg,image/png,image/webp"
                      className="hidden"
                      onChange={(e) => {
                        if (e.target.files) void addMoreFiles(Array.from(e.target.files));
                        e.target.value = "";
                      }}
                    />
                  </label>
                  <button
                    type="button"
                    onClick={exportCsv}
                    className="rounded-full bg-ink px-5 py-2 text-[13px] font-medium text-paper transition active:scale-[0.97] dark:bg-ink-dark dark:text-paper-dark"
                  >
                    Export script (.csv)
                  </button>
                </div>
              </div>
              {addMoreError && (
                <p className="mt-2 text-[12px] text-red-600/80 dark:text-red-400/80">{addMoreError}</p>
              )}
              {panels.length > MAX_COMICS_PANELS_HINT && (
                // Purely a heads-up, shown as soon as the count crosses the
                // line - "Adapt chapter" itself stays clickable, since only
                // server/main.py's own check (the real, authoritative one)
                // can say for certain a given deployment will reject it.
                // Without this, a chapter this large - most often an
                // auto-sliced whole-chapter strip, see
                // lib/chapterSlice.ts - silently let a user edit every
                // panel by hand before finding out at the very last step.
                <p className="mt-2 text-[12px] text-red-600/80 dark:text-red-400/80">
                  {panels.length} panels is over the usual {MAX_COMICS_PANELS_HINT}-panel limit for one
                  chapter - "Adapt chapter" will likely reject this. Consider removing some panels or
                  splitting this into shorter chapters before doing more editing.
                </p>
              )}

              <PanelOrderGrid panels={panels} onReorder={reorderPanels} />

              <div className="mt-4 flex flex-wrap items-center gap-3">
                {/* Only shown once a non-English target is picked, same as
                    InputScreen.tsx's music equivalent - server/main.py
                    only requires an explicit source_language for that
                    case. Unconditionally rendering this while both
                    languages default to "English" used to mean the
                    options list excluded "English" (it always excludes
                    whatever's selected as the target) with no matching
                    option for the value still set to "English" - the
                    browser silently fell back to selecting whatever
                    option happened to be first, so the dropdown showed a
                    language nobody picked while the real state underneath
                    still read "English". */}
                {targetLanguage !== "English" && (
                  <TargetLanguageSelect
                    label="From"
                    value={sourceLanguage}
                    onChange={(next) => {
                      setSourceLanguage(next);
                      setSourceLanguageTouched(true);
                    }}
                    options={LANGUAGES.filter((lang) => lang !== targetLanguage)}
                  />
                )}
                <TargetLanguageSelect
                  label="Adapt into"
                  value={targetLanguage}
                  onChange={(next) => {
                    setTargetLanguage(next);
                    if (next === sourceLanguage) {
                      setSourceLanguage(LANGUAGES.find((lang) => lang !== next) ?? "English");
                    }
                  }}
                />
                {signedIn && (
                  <label
                    className="inline-flex items-center gap-2 text-[13px]"
                    title="Same name as a previous chapter reuses that series' saved character voices/honorifics instead of guessing them fresh. Leave blank for no cross-chapter memory."
                  >
                    <span className="text-ink/62 dark:text-ink-dark/62">Series</span>
                    <input
                      type="text"
                      value={seriesName}
                      onChange={(e) => setSeriesName(e.target.value)}
                      placeholder="e.g. Solo Leveling (optional)"
                      className="rounded-full border border-black/[0.12] bg-white/70 px-3 py-1.5 text-[13px] text-ink placeholder:text-ink/45 outline-none transition focus:border-black/20 dark:border-white/[0.12] dark:bg-white/[0.03] dark:text-ink-dark dark:placeholder:text-ink-dark/45"
                    />
                  </label>
                )}
                {/* Reading a chapter one panel at a time meant one click
                    and one full round trip per panel; this runs the
                    unread ones a few at a time (lib/concurrency.ts).
                    Panels already read are skipped rather than re-sent -
                    each Cloud Vision call is real and metered. */}
                <button
                  type="button"
                  onClick={runOcrForAllPanels}
                  disabled={
                    batchOcrRunning ||
                    !panels.some((p) => p.ocrStatus === "idle" || p.ocrStatus === "error")
                  }
                  className="rounded-full border border-black/10 px-5 py-2 text-[13px] font-medium transition active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-40 dark:border-white/15"
                >
                  {batchOcrRunning
                    ? `Reading panels… (${panels.filter((p) => p.ocrStatus === "done").length}/${panels.length})`
                    : "Run OCR on all panels"}
                </button>
                <button
                  type="button"
                  onClick={adaptWholeChapter}
                  disabled={adaptStatus === "running" || !panels.some((p) => panelToChapterBubbles(p).length > 0)}
                  className="rounded-full bg-accent px-5 py-2 text-[13px] font-medium text-white transition active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {adaptStatus === "running"
                    ? adaptProgress
                      ? `Adapting… (${adaptProgress.completed}/${adaptProgress.total})`
                      : "Adapting chapter…"
                    : "Adapt chapter"}
                </button>
                {lastAdaptedId && <CopyLinkButton resultId={lastAdaptedId} basePath="/comics/s" />}
                {adaptError && (
                  <span className="text-[12px] text-red-500/80">{adaptError}</span>
                )}
              </div>
              {adaptStatus === "running" && adaptProgress && (
                <p className="mt-2 text-[12px] text-ink/75 dark:text-ink-dark/75">
                  {adaptProgress.message} · the panels below fill in as each one finishes - keep
                  reviewing or editing while the rest adapt.
                </p>
              )}

              <div className="mt-6">
                <PanelWorkspace
                  panels={panels}
                  onUpdatePanel={updatePanel}
                  onRemovePanel={removePanel}
                  onRunOcr={runOcr}
                  onRedrawPanel={redrawPanelAction}
                />
              </div>
            </>
          )}
        </div>

        <Footer />
      </div>
    </main>
  );
}

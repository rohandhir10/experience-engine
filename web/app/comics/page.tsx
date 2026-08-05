"use client";

import { useEffect, useState } from "react";
import { SiteHeader } from "@/components/SiteHeader";
import { CopyLinkButton } from "@/components/CopyLinkButton";
import { TargetLanguageSelect } from "@/components/TargetLanguageSelect";
import { PanelUploader } from "@/components/comics/PanelUploader";
import { PanelWorkspace } from "@/components/comics/PanelWorkspace";
import { naturalCompare } from "@/lib/naturalSort";
import { LANGUAGES } from "@/lib/languages";
import { panelsToCsv, type ComicPanel } from "@/lib/comics-types";
import { OcrRequestError, runPanelOcr } from "@/lib/comicsOcr";
import { OCR_BATCH_CONCURRENCY, runWithConcurrency } from "@/lib/concurrency";
import { guessChapterLanguage } from "@/lib/chapterLanguage";
import { AdaptRequestError, adaptChapter } from "@/lib/comicsAdapt";
import { RedrawRequestError, redrawPanel, resolveRedrawRegionText } from "@/lib/comicsRedraw";
import { writeMediumPreference } from "@/lib/mediumPreference";
import { ComicsPipelineDiagram } from "@/components/ComicsPipelineDiagram";
import { Footer } from "@/components/Footer";
import { ScrollReveal } from "@/components/ScrollReveal";

// Now linked from "/" (the Webtoons tile on the medium-chooser split
// screen) with a "Beta" badge, rather than reachable only by URL - it
// earned that entry point once OCR + a real adapt call both existed,
// per the project's non-fabrication discipline. Still genuinely behind
// music on feature parity, which is exactly what the badge discloses:
// no save/collections/share-link, and the adapt call below is still
// synchronous, so a long chapter can time out - no async job/poll
// pattern exists for this yet (music's /api/adapt/start + jobs/[jobId]
// is the pattern to eventually match). This page is that tool's
// functional foundation: file upload, a panel-by-panel review
// workspace, a real (if imperfect) OCR pass per panel
// (/api/comics/ocr), and a real adaptation call (/api/comics/adapt,
// engine/chapter_dna.py + engine/comics_adapt.py) - see that route's
// comments for what it does and doesn't do yet (each PANEL is one
// adaptation unit, not each detected OCR region).
export default function ComicsPage() {
  const [panels, setPanels] = useState<ComicPanel[]>([]);
  const [sourceLanguage, setSourceLanguage] = useState("English");
  const [sourceLanguageTouched, setSourceLanguageTouched] = useState(false);
  const [targetLanguage, setTargetLanguage] = useState("English");
  const [batchOcrRunning, setBatchOcrRunning] = useState(false);
  const [adaptStatus, setAdaptStatus] = useState<"idle" | "running" | "error">("idle");
  const [adaptError, setAdaptError] = useState<string | null>(null);
  // Set once a "Adapt chapter" call succeeds - server/main.py now persists
  // the result under this id (cache.comics_content_id), so it's real and
  // shareable, not a local-only id. Cleared on the next edit that would
  // make the persisted result stale (a panel added/removed, or another
  // adapt run), same "don't imply a link still matches what's on screen"
  // reasoning /s/[id] never has to think about since songs are read-only
  // once shared.
  const [lastAdaptedId, setLastAdaptedId] = useState<string | null>(null);

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
        redrawRegionTexts: null,
        redrawResultUrl: null,
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
      // A new OCR run means new region indices - any redraw state tied
      // to the old ones (per-region text, a composited result image)
      // no longer corresponds to anything real.
      redrawRegionTexts: null,
      redrawResultUrl: null,
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
      const dataUrl = await redrawPanel(panel.file, regionsToSend);
      updatePanel(id, { redrawStatus: "idle", redrawResultUrl: dataUrl, redrawMessage: null });
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

  async function adaptWholeChapter() {
    const eligiblePanels = panels.filter((p) => p.extractedText.trim());
    if (!eligiblePanels.length || adaptStatus === "running") return;
    setAdaptStatus("running");
    setAdaptError(null);
    try {
      const result = await adaptChapter(
        eligiblePanels.map((p) => ({ id: p.id, text: p.extractedText, voice: p.voice || undefined })),
        sourceLanguage,
        targetLanguage
      );
      for (const panelResult of result.panels) {
        const panel = panels.find((p) => p.id === panelResult.id);
        if (!panel) continue;
        updatePanel(panelResult.id, {
          // Only pre-fills an empty field - never overwrites text the
          // human has already reviewed/edited by hand, same rule
          // "Run OCR" already follows for extractedText.
          adaptedText: panel.adaptedText.trim() ? panel.adaptedText : panelResult.adaptedText,
          why: panel.why.trim() ? panel.why : panelResult.why,
        });
      }
      setAdaptStatus("idle");
      setLastAdaptedId(result.id || null);
    } catch (err) {
      setAdaptStatus("error");
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
          <p className="text-[12px] uppercase tracking-[0.15em] text-accent">
            CASTIA Comics — early scaffold
          </p>
          <h1 className="mt-2 font-serif text-2xl text-ink dark:text-ink-dark sm:text-[1.75rem]">
            Panel-by-panel script workspace
          </h1>
          <p className="mt-3 max-w-2xl text-[14px] leading-relaxed text-ink/50 dark:text-ink-dark/50">
            Upload a chapter's worth of panel images. "Run OCR" pulls real text out of a panel
            with Google Cloud Vision — it auto-detects the script and language, but it's still
            genuinely imperfect on stylized comic lettering, so treat it as a starting draft.
            "Adapt chapter" runs every panel's text through the same Reasoning Engine the music
            side uses — each panel is adapted as one block of dialogue for now, not split per
            speech bubble, and nothing yet tracks who's speaking from panel to panel.
          </p>

          {panels.length === 0 ? (
            <>
              <div className="mt-8">
                <PanelUploader onFilesSelected={addFiles} />
              </div>

              <ScrollReveal className="mx-auto mt-20 w-full max-w-4xl rounded-2xl bg-[#141a2b] p-8 sm:p-10">
                <p className="text-[12px] uppercase tracking-[0.15em] text-white/25">
                  Under the hood
                </p>
                <h2 className="mt-3 max-w-lg font-serif text-[1.5rem] leading-[1.25] text-white sm:text-[1.7rem]">
                  Real OCR, then the same Writers' Room as music.
                </h2>
                <p className="mt-3 max-w-xl text-[13px] leading-relaxed text-white/40">
                  A chapter's panels go through Google Cloud Vision, then Chapter DNA (the
                  cast/tone profile for the whole chapter), then the identical
                  Translator → Creative Adapter → Judge pipeline the music side uses — not
                  a separate, lesser engine.
                </p>
                <div className="mt-8">
                  <ComicsPipelineDiagram />
                </div>
              </ScrollReveal>
            </>
          ) : (
            <>
              <div className="mt-8 flex flex-wrap items-center justify-between gap-3">
                <div className="flex flex-wrap items-center gap-3">
                  <p className="text-[13px] text-ink/45 dark:text-ink-dark/45">
                    {panels.length} panel{panels.length === 1 ? "" : "s"} loaded
                  </p>
                  {chapterLanguage && (
                    <span className="rounded-full border border-black/[0.08] px-3 py-1 text-[12px] text-ink/50 dark:border-white/[0.08] dark:text-ink-dark/50">
                      Detected language: {chapterLanguage.languageName ?? chapterLanguage.languageCode}
                      {chapterLanguage.ocrdPanelCount > 1 &&
                        ` (${chapterLanguage.agreeingPanelCount} of ${chapterLanguage.ocrdPanelCount} OCR'd panels)`}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-4">
                  <label className="cursor-pointer text-[13px] text-ink/45 underline decoration-ink/15 underline-offset-4 transition hover:text-ink/70 hover:decoration-ink/30 dark:text-ink-dark/45 dark:decoration-ink-dark/15 dark:hover:text-ink-dark/70">
                    Add more
                    <input
                      type="file"
                      multiple
                      accept="image/jpeg,image/png,image/webp"
                      className="hidden"
                      onChange={(e) => {
                        if (e.target.files) addFiles(Array.from(e.target.files));
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

              <div className="mt-4 flex flex-wrap items-center gap-3">
                <TargetLanguageSelect
                  label="From"
                  value={sourceLanguage}
                  onChange={(next) => {
                    setSourceLanguage(next);
                    setSourceLanguageTouched(true);
                  }}
                  options={LANGUAGES.filter((lang) => lang !== targetLanguage)}
                />
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
                  disabled={adaptStatus === "running" || !panels.some((p) => p.extractedText.trim())}
                  className="rounded-full bg-accent px-5 py-2 text-[13px] font-medium text-white transition active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {adaptStatus === "running" ? "Adapting chapter…" : "Adapt chapter"}
                </button>
                {lastAdaptedId && <CopyLinkButton resultId={lastAdaptedId} basePath="/comics/s" />}
                {adaptError && (
                  <span className="text-[12px] text-red-500/80">{adaptError}</span>
                )}
              </div>

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

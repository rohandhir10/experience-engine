"use client";

import { useState } from "react";
import { SiteHeader } from "@/components/SiteHeader";
import { PanelUploader } from "@/components/comics/PanelUploader";
import { PanelWorkspace } from "@/components/comics/PanelWorkspace";
import { naturalCompare } from "@/lib/naturalSort";
import { panelsToCsv, type ComicPanel } from "@/lib/comics-types";

// Not linked from primary nav or the marketing homepage - reachable only
// by URL, same convention as /alternate-homepage. Per the project's
// non-fabrication discipline, the homepage won't pitch a Comics
// workspace until there's a real, working tool to show a real
// screenshot of. This page is that tool's functional foundation: file
// upload plus a panel-by-panel review workspace. It has no backend yet
// (see the banner below) - the shared Reasoning Engine (OCR extraction,
// automated adaptation) is a separate, later integration, not
// scaffolded here.
export default function ComicsPage() {
  const [panels, setPanels] = useState<ComicPanel[]>([]);

  function addFiles(files: File[]) {
    const newPanels: ComicPanel[] = files
      .map((file) => ({
        id: `${file.name}-${file.size}-${file.lastModified}`,
        fileName: file.name,
        previewUrl: URL.createObjectURL(file),
        extractedText: "",
        adaptedText: "",
        why: "",
      }))
      .sort((a, b) => naturalCompare(a.fileName, b.fileName));

    setPanels((prev) => {
      const existingIds = new Set(prev.map((p) => p.id));
      const merged = [...prev, ...newPanels.filter((p) => !existingIds.has(p.id))];
      return merged.sort((a, b) => naturalCompare(a.fileName, b.fileName));
    });
  }

  function updatePanel(id: string, patch: Partial<ComicPanel>) {
    setPanels((prev) => prev.map((p) => (p.id === id ? { ...p, ...patch } : p)));
  }

  function removePanel(id: string) {
    setPanels((prev) => {
      const target = prev.find((p) => p.id === id);
      if (target) URL.revokeObjectURL(target.previewUrl);
      return prev.filter((p) => p.id !== id);
    });
  }

  function exportCsv() {
    const blob = new Blob([panelsToCsv(panels)], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "aura-comics-script.csv";
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <main className="min-h-screen px-6 pb-28 pt-8 sm:px-10">
      <div className="mx-auto max-w-5xl">
        <SiteHeader />

        <div className="mt-10">
          <p className="text-[12px] uppercase tracking-[0.15em] text-accent">
            AURA Comics — early scaffold
          </p>
          <h1 className="mt-2 font-serif text-2xl text-ink dark:text-ink-dark sm:text-[1.75rem]">
            Panel-by-panel script workspace
          </h1>
          <p className="mt-3 max-w-2xl text-[14px] leading-relaxed text-ink/50 dark:text-ink-dark/50">
            Upload a chapter's worth of panel images and draft a literal/adapted script for each
            one. Nothing here is connected to OCR or the Reasoning Engine yet — extracted and
            adapted text are plain fields you fill in by hand. This is the workspace's functional
            foundation; automatic caption extraction and adaptation are a separate step, not yet
            built.
          </p>

          {panels.length === 0 ? (
            <div className="mt-8">
              <PanelUploader onFilesSelected={addFiles} />
            </div>
          ) : (
            <>
              <div className="mt-8 flex flex-wrap items-center justify-between gap-3">
                <p className="text-[13px] text-ink/45 dark:text-ink-dark/45">
                  {panels.length} panel{panels.length === 1 ? "" : "s"} loaded
                </p>
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

              <div className="mt-6">
                <PanelWorkspace
                  panels={panels}
                  onUpdatePanel={updatePanel}
                  onRemovePanel={removePanel}
                />
              </div>
            </>
          )}
        </div>
      </div>
    </main>
  );
}

"use client";

import { useRef, useState } from "react";
import { SiteHeader } from "@/components/SiteHeader";
import { DashboardSidebar } from "@/components/DashboardSidebar";
import { LoadingScreen } from "@/components/LoadingScreen";
import { TargetLanguageSelect } from "@/components/TargetLanguageSelect";
import { RecentAdaptations } from "@/components/RecentAdaptations";
import { useAdaptSubmit } from "@/lib/useAdaptSubmit";
import { detectSourceLanguage } from "@/lib/detectLanguage";
import { LANGUAGES, sourceHintFor } from "@/lib/languages";

const MIN_ROWS = 5;
const MAX_TEXTAREA_HEIGHT_PX = 320;

export default function DashboardPage() {
  const { submit, loading, error } = useAdaptSubmit();
  const [text, setText] = useState("");
  const [targetLanguage, setTargetLanguage] = useState("English");
  const [sourceLanguage, setSourceLanguage] = useState("English");
  // Once the user has explicitly picked a "From" language themselves,
  // auto-detection stops overwriting it.
  const [sourceLanguageTouched, setSourceLanguageTouched] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const effectiveSourceLanguage = targetLanguage === "English" ? undefined : sourceLanguage;

  if (loading) {
    return <LoadingScreen />;
  }

  function autoGrow(el: HTMLTextAreaElement) {
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, MAX_TEXTAREA_HEIGHT_PX)}px`;
  }

  return (
    <main className="min-h-screen px-6 pb-28 pt-8 sm:px-10">
      <div className="mx-auto max-w-5xl">
        <SiteHeader />

        <div className="mt-10 flex flex-col gap-10 sm:flex-row">
          <DashboardSidebar active="home" />

          <div className="min-w-0 flex-1">
            <h1 className="font-serif text-2xl text-ink dark:text-ink-dark sm:text-[1.75rem]">
              What would you like to adapt today?
            </h1>
            <p className="mt-2 text-[13px] text-ink/40 dark:text-ink-dark/40">
              {sourceHintFor(targetLanguage, sourceLanguage)}
            </p>

            <div className="mt-4 flex flex-wrap items-center gap-3">
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
            </div>

            <form
              className="mt-5 w-full max-w-2xl"
              onSubmit={(e) => {
                e.preventDefault();
                if (text.trim() && !loading) submit(text, targetLanguage, effectiveSourceLanguage);
              }}
            >
              <label htmlFor="dashboard-lyrics" className="sr-only">
                Paste song lyrics
              </label>
              <textarea
                ref={textareaRef}
                id="dashboard-lyrics"
                value={text}
                onChange={(e) => {
                  setText(e.target.value);
                  autoGrow(e.target);
                  if (!sourceLanguageTouched) {
                    const detected = detectSourceLanguage(e.target.value);
                    if (detected && detected !== targetLanguage) {
                      setSourceLanguage(detected);
                    }
                  }
                }}
                onKeyDown={(e) => {
                  if ((e.metaKey || e.ctrlKey) && e.key === "Enter" && text.trim()) {
                    e.preventDefault();
                    submit(text, targetLanguage, effectiveSourceLanguage);
                  }
                }}
                placeholder="Paste song lyrics…"
                rows={MIN_ROWS}
                className="w-full resize-none overflow-y-auto rounded-2xl border border-black/[0.08] bg-white/70 px-6 py-5 text-[15px] leading-relaxed text-ink placeholder:text-ink/30 transition dark:border-white/[0.08] dark:bg-white/[0.03] dark:text-ink-dark dark:placeholder:text-ink-dark/30"
              />

              {error && (
                <p role="alert" className="mt-3 text-[13px] text-red-500/80">
                  {error}
                </p>
              )}

              <div className="mt-5">
                <button
                  type="submit"
                  disabled={!text.trim()}
                  className="inline-flex items-center justify-center rounded-full bg-ink px-8 py-3 text-[14px] font-medium text-paper transition active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-30 dark:bg-ink-dark dark:text-paper-dark"
                >
                  Adapt Song
                </button>
              </div>
            </form>

            <div className="mt-16 border-t border-black/[0.05] pt-8 dark:border-white/[0.05]">
              <h2 className="text-[13px] font-medium uppercase tracking-[0.1em] text-ink/40 dark:text-ink-dark/40">
                Recent Adaptations
              </h2>
              <RecentAdaptations />
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}

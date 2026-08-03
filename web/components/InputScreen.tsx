"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { SiteHeader } from "./SiteHeader";
import { SystemComparisonCard } from "./SystemComparisonCard";
import { Logo } from "./Logo";
import { comparisonEntries } from "@/lib/comparison-data";

const MIN_ROWS = 6;
const MAX_TEXTAREA_HEIGHT_PX = 380;

export function InputScreen({
  onSubmit,
  loading,
  error,
}: {
  onSubmit: (text: string) => void;
  loading: boolean;
  error: string | null;
}) {
  const [text, setText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  function submit() {
    if (text.trim() && !loading) onSubmit(text);
  }

  function autoGrow(el: HTMLTextAreaElement) {
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, MAX_TEXTAREA_HEIGHT_PX)}px`;
  }

  const featured = comparisonEntries[0];
  const featuredAura = featured?.sections[0]?.systems.aura;
  const featuredSource = featured?.sections[0]?.source;

  return (
    <main className="flex flex-col">
      {/* Dark hero: unlike the rest of the site, this commits to one look
          regardless of system light/dark mode, matching the reference
          marketing design. There's no "Log in" / "Sign up" here — AURA has
          no accounts — and no Pricing/Enterprise/Community/Resources nav,
          since none of those exist. The only real nav destination beyond
          home is the comparison page. */}
      <section className="relative overflow-hidden bg-[#0b0b0c] px-6 pb-20 pt-8 sm:px-10">
        <div className="mx-auto flex max-w-5xl items-center justify-between">
          <Link href="/">
            <Logo force="light" />
          </Link>
          <Link
            href="/compare"
            className="text-[13px] text-white/45 transition hover:text-white/75"
          >
            Compare
          </Link>
        </div>

        <div className="mx-auto mt-16 flex max-w-2xl flex-col items-center text-center sm:mt-24">
          <h1 className="animate-fade-up text-[2.6rem] font-semibold leading-[1.08] tracking-tight text-white sm:text-[3.4rem]">
            Adapt the feeling.
            <br />
            Not just the words.
          </h1>
          <p
            className="animate-fade-up mt-5 max-w-md text-[15px] leading-relaxed text-white/45"
            style={{ animationDelay: "80ms" }}
          >
            Paste lyrics in Hindi, Korean, Japanese, or Spanish. AURA
            re-writes them in English so the meaning still lands — not a
            literal translation.
          </p>

          <form
            className="animate-fade-up mt-10 w-full"
            style={{ animationDelay: "160ms" }}
            onSubmit={(e) => {
              e.preventDefault();
              submit();
            }}
          >
            <label htmlFor="lyrics" className="sr-only">
              Paste song lyrics
            </label>
            <textarea
              ref={textareaRef}
              id="lyrics"
              value={text}
              onChange={(e) => {
                setText(e.target.value);
                autoGrow(e.target);
              }}
              onKeyDown={(e) => {
                if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
                  e.preventDefault();
                  submit();
                }
              }}
              placeholder="Paste song lyrics…"
              rows={MIN_ROWS}
              autoFocus
              aria-describedby={error ? "lyrics-error" : undefined}
              className="w-full resize-none overflow-y-auto rounded-2xl border border-white/10 bg-white/[0.04] px-6 py-5 text-[15px] leading-relaxed text-white placeholder:text-white/25 transition focus:border-white/20"
            />

            {error && (
              <p
                id="lyrics-error"
                role="alert"
                className="mt-3 text-[13px] text-red-400/80"
              >
                {error}
              </p>
            )}

            <div className="mt-7 flex flex-wrap items-center justify-center gap-3">
              <button
                type="submit"
                disabled={!text.trim() || loading}
                className="inline-flex items-center justify-center gap-2 rounded-full bg-white px-8 py-3 text-[14px] font-medium text-black transition active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-30"
              >
                {loading && (
                  <span className="h-3 w-3 animate-spin rounded-full border-[1.5px] border-black/30 border-t-black" />
                )}
                {loading ? "Listening" : "Experience it"}
              </button>

              <Link
                href="/s/demo"
                className="inline-flex items-center justify-center rounded-full border border-white/15 px-8 py-3 text-[14px] font-medium text-white/80 transition hover:border-white/30 hover:text-white"
              >
                See an example
              </Link>
            </div>

            {text.trim() && !loading && (
              <p className="animate-fade-up mt-4 text-center text-[12px] text-white/25">
                ⌘ + Enter
              </p>
            )}
          </form>
        </div>

        {featured && featuredAura && (
          <div
            className="animate-fade-up mx-auto mt-20 w-full max-w-3xl"
            style={{ animationDelay: "240ms" }}
          >
            <div className="overflow-hidden rounded-2xl border border-white/10 bg-white/[0.02]">
              <div className="flex items-center gap-2 border-b border-white/10 px-5 py-3">
                <span className="h-2.5 w-2.5 rounded-full bg-white/15" />
                <span className="h-2.5 w-2.5 rounded-full bg-white/15" />
                <span className="h-2.5 w-2.5 rounded-full bg-white/15" />
                <span className="ml-3 text-[12px] text-white/35">
                  {featured.title} — real production run
                </span>
              </div>
              <div className="grid gap-6 px-6 py-7 sm:grid-cols-2 sm:px-8">
                <div>
                  <p className="text-[11px] font-medium uppercase tracking-[0.15em] text-white/30">
                    Original
                  </p>
                  <p className="mt-3 whitespace-pre-line text-[14px] leading-relaxed text-white/40">
                    {featuredSource}
                  </p>
                </div>
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.15em] text-accent">
                    AURA
                  </p>
                  <p className="mt-3 whitespace-pre-line text-[16px] leading-relaxed text-white">
                    {featuredAura}
                  </p>
                </div>
              </div>
              <div className="border-t border-white/10 px-6 py-3 text-right sm:px-8">
                <Link
                  href="/compare"
                  className="text-[13px] text-white/45 transition hover:text-white/75"
                >
                  See the full comparison, unedited →
                </Link>
              </div>
            </div>
          </div>
        )}
      </section>

      {featured && (
        <div className="px-6 sm:px-10">
          <SiteHeader active="home" />
          <section className="mx-auto mb-28 mt-14 w-full max-w-3xl">
            <div className="flex items-baseline justify-between gap-4">
              <h2 className="font-serif text-2xl text-ink dark:text-ink-dark sm:text-[1.75rem]">
                See the difference.
              </h2>
              <Link
                href="/compare"
                className="whitespace-nowrap text-[13px] text-ink/45 transition hover:text-ink/70 dark:text-ink-dark/45 dark:hover:text-ink-dark/70"
              >
                More examples →
              </Link>
            </div>
            <p className="mt-3 max-w-prose text-[14px] leading-relaxed text-ink/45 dark:text-ink-dark/45">
              Same source lyric, run through Google Translate, a single GPT
              prompt, and AURA — {featured.title}, a real production run,
              not a cherry-picked demo.
            </p>
            <div className="mt-8">
              <SystemComparisonCard section={featured.sections[0]} index={0} />
            </div>
          </section>
        </div>
      )}
    </main>
  );
}

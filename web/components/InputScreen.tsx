"use client";

import { useState } from "react";
import { Logo } from "./Logo";

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

  function submit() {
    if (text.trim() && !loading) onSubmit(text);
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-6">
      <div className="fixed left-6 top-6 sm:left-10 sm:top-10">
        <Logo />
      </div>

      <div className="flex w-full max-w-xl flex-col items-center text-center">
        <h1 className="animate-fade-up font-serif text-[2.35rem] leading-[1.15] tracking-tight text-ink dark:text-ink-dark sm:text-[2.75rem]">
          Songs, not just their words.
        </h1>
        <p
          className="animate-fade-up mt-4 text-[15px] text-ink/50 dark:text-ink-dark/50"
          style={{ animationDelay: "80ms" }}
        >
          Paste the lyrics. Feel what they actually mean.
        </p>

        <form
          className="animate-fade-up mt-12 w-full"
          style={{ animationDelay: "160ms" }}
          onSubmit={(e) => {
            e.preventDefault();
            submit();
          }}
        >
          <label htmlFor="lyrics" className="sr-only">
            Paste lyrics or dialogue
          </label>
          <textarea
            id="lyrics"
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
                e.preventDefault();
                submit();
              }
            }}
            placeholder="Paste lyrics or dialogue…"
            rows={7}
            autoFocus
            aria-describedby={error ? "lyrics-error" : undefined}
            className="w-full resize-none rounded-2xl border border-black/[0.08] bg-white/70 px-6 py-5 text-[15px] leading-relaxed text-ink placeholder:text-ink/30 transition dark:border-white/[0.08] dark:bg-white/[0.03] dark:text-ink-dark dark:placeholder:text-ink-dark/30"
          />

          {error && (
            <p
              id="lyrics-error"
              role="alert"
              className="mt-3 text-[13px] text-red-500/80"
            >
              {error}
            </p>
          )}

          <div className="mt-6 flex items-center justify-center gap-4">
            <button
              type="submit"
              disabled={!text.trim() || loading}
              className="inline-flex items-center justify-center gap-2 rounded-full bg-ink px-8 py-3 text-[14px] font-medium text-paper transition active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-30 dark:bg-ink-dark dark:text-paper-dark"
            >
              {loading && (
                <span className="h-3 w-3 animate-spin rounded-full border-[1.5px] border-paper/40 border-t-paper dark:border-paper-dark/40 dark:border-t-paper-dark" />
              )}
              {loading ? "Listening" : "Experience it"}
            </button>

            {text.trim() && !loading && (
              <span className="animate-fade-up text-[12px] text-ink/30 dark:text-ink-dark/30">
                ⌘ + Enter
              </span>
            )}
          </div>
        </form>
      </div>
    </main>
  );
}

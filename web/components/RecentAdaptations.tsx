"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

type HistoryEntry = {
  resultId: string;
  createdAt: string;
  isFavorite: boolean;
  hook: string | null;
  sourceLanguage: string | null;
  targetLanguage: string | null;
};

type HistoryState =
  | { status: "loading" }
  | { status: "signed-out" }
  | { status: "error" }
  | { status: "ready"; entries: HistoryEntry[] };

// The dashboard's history list, backed by /api/me/adaptations (which is
// empty-with-signedIn:false for anonymous visitors rather than an error -
// history is an account perk, not a requirement). Each entry links to the
// same shareable /s/[id] page the original submission landed on.
export function RecentAdaptations() {
  const [state, setState] = useState<HistoryState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    fetch("/api/me/adaptations")
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error(String(res.status)))))
      .then((body) => {
        if (cancelled) return;
        if (!body.signedIn) setState({ status: "signed-out" });
        else setState({ status: "ready", entries: body.adaptations ?? [] });
      })
      .catch(() => {
        if (!cancelled) setState({ status: "error" });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (state.status === "loading") {
    return (
      <p className="mt-4 text-[14px] text-ink/30 dark:text-ink-dark/30">Loading…</p>
    );
  }
  if (state.status === "signed-out") {
    return (
      <p className="mt-4 text-[14px] leading-relaxed text-ink/40 dark:text-ink-dark/40">
        <Link href="/sign-in" className="underline decoration-ink/20 underline-offset-4 hover:text-ink/70 dark:decoration-ink-dark/20 dark:hover:text-ink-dark/70">
          Sign in
        </Link>{" "}
        to keep a history of the songs you adapt.
      </p>
    );
  }
  if (state.status === "error") {
    return (
      <p className="mt-4 text-[14px] text-ink/40 dark:text-ink-dark/40">
        Couldn't load your history right now — your adaptations are still
        saved.
      </p>
    );
  }
  if (state.entries.length === 0) {
    return (
      <p className="mt-4 text-[14px] leading-relaxed text-ink/40 dark:text-ink-dark/40">
        No adaptations yet — the first song you adapt will show up here.
      </p>
    );
  }
  return (
    <ul className="mt-4 divide-y divide-black/[0.05] dark:divide-white/[0.05]">
      {state.entries.map((entry) => (
        <li key={entry.resultId}>
          <Link
            href={`/s/${entry.resultId}`}
            className="group flex items-baseline justify-between gap-4 py-3"
          >
            <span className="min-w-0 truncate text-[14px] text-ink/75 transition group-hover:text-ink dark:text-ink-dark/75 dark:group-hover:text-ink-dark">
              {entry.hook || "Untitled adaptation"}
            </span>
            <span className="shrink-0 text-[12px] text-ink/35 dark:text-ink-dark/35">
              {[entry.sourceLanguage, entry.targetLanguage].filter(Boolean).join(" → ")}
              {" · "}
              {new Date(entry.createdAt).toLocaleDateString()}
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}

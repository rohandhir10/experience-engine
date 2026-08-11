"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { SiteHeader } from "@/components/SiteHeader";
import { CopyLinkButton } from "@/components/CopyLinkButton";
import { LoadingScreen } from "@/components/LoadingScreen";

type ComicsResult = {
  id: string;
  chapter_dna: {
    artistic_thesis: string;
    genre_feel: string;
    tone: string;
  };
  panels: { id: string; literal: string; adapted_text: string; why: string }[];
};

// Read-only comics-share equivalent of app/s/[id]/page.tsx - the first
// time a comics chapter result has ever been persisted and linkable
// rather than living only in one browser tab's React state (see
// server/main.py's comics_adapt_endpoint + GET /api/comics/adapt/{id}).
// No sessionStorage fast path like the song page has, since nothing
// stashes a comics result client-side before navigating here yet - every
// load is a real network fetch. Deliberately simpler than ResultScreen:
// no original-panel-image toggle (the persisted result never stored the
// uploaded images, only the adapted text), no YouTube sync - just the
// literal/adapted/why per panel, same idiom, comics-appropriate shape.
async function fetchResult(id: string): Promise<ComicsResult | null> {
  try {
    const res = await fetch(`/api/comics/adapt/${id}`, { cache: "no-store" });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export default function ComicsSharedResultPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const [result, setResult] = useState<ComicsResult | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchResult(id).then((fetched) => {
      setResult(fetched);
      setLoading(false);
    });
  }, [id]);

  if (loading) {
    return <LoadingScreen />;
  }

  if (!result) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center px-6 text-center">
        <p className="font-serif text-2xl text-ink dark:text-ink-dark">
          This link doesn't lead anywhere anymore.
        </p>
        <p className="mt-3 text-[15px] text-ink/68 dark:text-ink-dark/68">
          The chapter it pointed to may not have been adapted yet on this engine.
        </p>
        <Link
          href="/comics"
          className="mt-8 rounded-full bg-ink px-8 py-3 text-[14px] font-medium text-paper transition active:scale-[0.97] dark:bg-ink-dark dark:text-paper-dark"
        >
          Adapt a chapter
        </Link>
      </main>
    );
  }

  return (
    <main className="min-h-screen px-6 pb-28 pt-8 sm:px-10">
      <SiteHeader
        active="webtoons"
        right={
          <>
            <CopyLinkButton resultId={result.id} basePath="/comics/s" />
            <Link
              href="/comics"
              className="text-[13px] text-ink/65 transition hover:text-ink/78 dark:text-ink-dark/65 dark:hover:text-ink-dark/78"
            >
              ← Start over
            </Link>
          </>
        }
      />

      <div className="mx-auto max-w-2xl">
        <div className="mt-16 text-center sm:mt-20">
          <p className="text-[12px] uppercase tracking-[0.15em] text-accent">
            {result.chapter_dna.genre_feel} — {result.chapter_dna.tone}
          </p>
          <p className="mx-auto mt-3 max-w-lg text-[15px] leading-relaxed text-ink/72 dark:text-ink-dark/72">
            {result.chapter_dna.artistic_thesis}
          </p>
        </div>

        <div className="mt-14 flex flex-col gap-6">
          {result.panels.map((panel, i) => (
            <div
              key={panel.id}
              className="rounded-2xl border border-black/[0.12] bg-white/70 p-5 dark:border-white/[0.12] dark:bg-white/[0.03]"
            >
              <p className="text-[11px] uppercase tracking-wide text-ink/50 dark:text-ink-dark/50">
                Panel {i + 1}
              </p>
              <p className="mt-2 text-[13px] italic leading-relaxed text-ink/65 dark:text-ink-dark/65">
                {panel.literal}
              </p>
              <p className="mt-2 text-[15px] leading-relaxed text-ink dark:text-ink-dark">
                {panel.adapted_text}
              </p>
              <p className="mt-3 text-[12px] leading-relaxed text-ink/62 dark:text-ink-dark/62">
                {panel.why}
              </p>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}

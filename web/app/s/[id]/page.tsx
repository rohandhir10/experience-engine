"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import type { ExperienceResult } from "@/lib/types";
import { Logo } from "@/components/Logo";
import { ResultScreen } from "@/components/ResultScreen";
import { LoadingScreen } from "@/components/LoadingScreen";
import { demoResult } from "@/lib/demo-data";

// Client component: sessionStorage (written by app/page.tsx right after
// a successful submission) is the fastest source for this page's data
// and needs the browser, not a server component. The network fallback
// below now hits a real persistent Railway service (server/cache.py's
// store lives on that one process's disk, not a fresh /tmp per request
// the way Vercel serverless functions worked) - so a page refresh or a
// link shared with someone else should actually find it, as long as the
// service hasn't redeployed since (a fresh container's disk starts empty
// unless a volume is attached - see Dockerfile's comment on this).
async function fetchResult(id: string): Promise<ExperienceResult | null> {
  try {
    const res = await fetch(`/api/adapt/${id}`, { cache: "no-store" });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export default function SharedResultPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const [result, setResult] = useState<ExperienceResult | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (id === "demo") {
      setResult(demoResult);
      setLoading(false);
      return;
    }

    const stashed = sessionStorage.getItem(`castia-result-${id}`);
    if (stashed) {
      try {
        setResult(JSON.parse(stashed));
        setLoading(false);
        return;
      } catch {
        // Fall through to the network fetch below.
      }
    }

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
        <div className="fixed left-6 top-6 sm:left-10 sm:top-10">
          <Logo />
        </div>
        <p className="font-serif text-2xl text-ink dark:text-ink-dark">
          This link doesn't lead anywhere anymore.
        </p>
        <p className="mt-3 text-[15px] text-ink/50 dark:text-ink-dark/50">
          The song it pointed to may not have been experienced yet on this
          engine.
        </p>
        <Link
          href="/"
          className="mt-8 rounded-full bg-ink px-8 py-3 text-[14px] font-medium text-paper transition active:scale-[0.97] dark:bg-ink-dark dark:text-paper-dark"
        >
          Experience a song
        </Link>
      </main>
    );
  }

  return <ResultScreen result={result} />;
}

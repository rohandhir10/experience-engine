"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { InputScreen } from "@/components/InputScreen";
import { LoadingScreen } from "@/components/LoadingScreen";

export default function Home() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(text: string) {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/adapt", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(body.error || body.detail || "Something went wrong.");
      }
      // Stashed for the share page to read directly, client-side, so
      // viewing your own just-created result never needs a second network
      // round-trip at all - the fastest path, not a workaround for a
      // broken one. The share page's network fallback (for a refresh, or
      // a link opened by someone else) hits the same Railway-hosted
      // engine's own cache (server/cache.py), which is real and shared
      // across requests now, not per-request ephemeral the way it was on
      // Vercel serverless functions.
      try {
        sessionStorage.setItem(`aura-result-${body.id}`, JSON.stringify(body));
      } catch {
        // sessionStorage can throw in rare cases (private browsing quirks,
        // storage disabled) - the share page's network fallback still
        // covers this, just with the same disclosed cache limitation.
      }
      router.push(`/s/${body.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
      setLoading(false);
    }
  }

  if (loading) {
    return <LoadingScreen />;
  }

  return (
    <InputScreen onSubmit={handleSubmit} loading={loading} error={error} />
  );
}

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
      // Stashed for the share page to read directly, client-side, instead
      // of re-fetching over the network. The Python engine function wrote
      // its result to server/cache.py's store, but that store now lives on
      // /tmp inside that function's own container - a completely separate
      // runtime from this Next.js page, sharing no filesystem with it.
      // Re-fetching from here would fail every time, not just sometimes.
      // This only fixes the "view my own just-created result" case; a
      // link shared to someone else still depends on that cache, which
      // remains best-effort (see server/cache.py's docstring).
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

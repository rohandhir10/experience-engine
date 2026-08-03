"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

/** Shared by every surface that can submit lyrics for adaptation (the
 * marketing homepage, the dashboard) so the fetch/stash/navigate flow
 * isn't duplicated — see app/page.tsx's original comments for why the
 * result is stashed in sessionStorage before navigating. */
export function useAdaptSubmit() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(text: string) {
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
      try {
        sessionStorage.setItem(`aura-result-${body.id}`, JSON.stringify(body));
      } catch {
        // Covered by the share page's network fallback.
      }
      router.push(`/s/${body.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
      setLoading(false);
    }
  }

  return { submit, loading, error };
}

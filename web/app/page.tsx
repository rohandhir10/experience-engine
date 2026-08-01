"use client";

import { useState } from "react";
import type { ExperienceResult } from "@/lib/types";
import { InputScreen } from "@/components/InputScreen";
import { ResultScreen } from "@/components/ResultScreen";

export default function Home() {
  const [result, setResult] = useState<ExperienceResult | null>(null);
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
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.error || "Something went wrong.");
      }
      const data: ExperienceResult = await res.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  if (result) {
    return <ResultScreen result={result} onReset={() => setResult(null)} />;
  }

  return (
    <InputScreen onSubmit={handleSubmit} loading={loading} error={error} />
  );
}

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

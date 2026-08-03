"use client";

import { InputScreen } from "@/components/InputScreen";
import { LoadingScreen } from "@/components/LoadingScreen";
import { useAdaptSubmit } from "@/lib/useAdaptSubmit";

export default function Home() {
  const { submit, loading, error } = useAdaptSubmit();

  if (loading) {
    return <LoadingScreen />;
  }

  return <InputScreen onSubmit={submit} loading={loading} error={error} />;
}

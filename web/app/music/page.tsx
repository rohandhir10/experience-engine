"use client";

import { InputScreen } from "@/components/InputScreen";
import { LoadingScreen } from "@/components/LoadingScreen";
import { useAdaptSubmit } from "@/lib/useAdaptSubmit";

// Moved from app/page.tsx unchanged, as part of splitting "/" into a
// medium chooser (this page vs. app/comics/page.tsx) rather than "/"
// being the music workflow directly - see app/page.tsx's comment for
// why. Nothing about InputScreen/useAdaptSubmit itself changed.
export default function MusicPage() {
  const { submit, loading, error } = useAdaptSubmit();

  if (loading) {
    return <LoadingScreen />;
  }

  return <InputScreen onSubmit={submit} loading={loading} error={error} />;
}

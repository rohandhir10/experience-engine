"use client";

import { useEffect } from "react";
import { InputScreen } from "@/components/InputScreen";
import { LoadingScreen } from "@/components/LoadingScreen";
import { useAdaptSubmit } from "@/lib/useAdaptSubmit";
import { writeMediumPreference } from "@/lib/mediumPreference";

// Moved from app/page.tsx unchanged, as part of splitting "/" into a
// medium chooser (this page vs. app/comics/page.tsx) rather than "/"
// being the music workflow directly - see app/page.tsx's comment for
// why. Nothing about InputScreen/useAdaptSubmit itself changed.
export default function MusicPage() {
  const { submit, loading, error, progress } = useAdaptSubmit();

  // Written on every real arrival here - a tile click from "/", the
  // header's MediumSwitcher (which also writes this, redundantly but
  // harmlessly, before navigating), or a direct URL/bookmark - so "/"'s
  // read/redirect reflects wherever someone actually ends up, not just
  // where they clicked from the chooser.
  useEffect(() => {
    writeMediumPreference("music");
  }, []);

  if (loading) {
    return <LoadingScreen progress={progress} />;
  }

  return <InputScreen onSubmit={submit} loading={loading} error={error} />;
}

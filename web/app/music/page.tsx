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

  // InputScreen stays mounted the whole time, even while loading - it
  // holds the pasted lyrics (and every other input) in its own local
  // state, so swapping it out for LoadingScreen used to unmount it and
  // wipe everything typed the moment a submit failed, before the error
  // even had a chance to render. LoadingScreen overlays on top instead,
  // the same "don't lose what the user already did" reasoning as
  // app/comics/page.tsx keeping its panel state above the loading branch.
  return (
    <>
      <InputScreen onSubmit={submit} loading={loading} error={error} />
      {loading && (
        <div className="fixed inset-0 z-50 bg-paper-dark">
          <LoadingScreen progress={progress} />
        </div>
      )}
    </>
  );
}

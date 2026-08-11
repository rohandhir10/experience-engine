"use client";

import { useRouter } from "next/navigation";
import { writeMediumPreference, type Medium } from "@/lib/mediumPreference";

// Extracted out of SiteHeader (which is rendered from both server and
// client trees and can't itself hold interactive state without a wider
// refactor - see SiteHeader.tsx's doc comment) so that constraint holds
// everywhere except the two medium-specific workspaces that actually
// need this control. Writes the visited medium to localStorage
// (lib/mediumPreference.ts) so a future visit to "/" skips the chooser
// and goes straight there - see app/page.tsx's read/redirect side.
export function MediumSwitcher({
  active,
  forceDark,
}: {
  active: Medium;
  forceDark?: boolean;
}) {
  const router = useRouter();

  function go(next: Medium) {
    if (next === active) return;
    writeMediumPreference(next);
    router.push(next === "music" ? "/music" : "/comics");
  }

  const border = forceDark ? "border-white/10" : "border-black/[0.12] dark:border-white/[0.12]";
  const activeClass = forceDark ? "bg-white/10 text-white/90" : "bg-black/[0.05] text-ink dark:bg-white/10 dark:text-ink-dark";
  const inactiveClass = forceDark
    ? "text-white/62 hover:text-white/78"
    : "text-ink/62 hover:text-ink/78 dark:text-ink-dark/62 dark:hover:text-ink-dark/78";

  return (
    <div className={`hidden items-center gap-1 rounded-full border p-0.5 text-[12px] sm:flex ${border}`}>
      {(["music", "webtoons"] as const).map((medium) => (
        <button
          key={medium}
          type="button"
          onClick={() => go(medium)}
          className={`rounded-full px-2.5 py-1 capitalize transition ${
            active === medium ? activeClass : inactiveClass
          }`}
        >
          {medium}
        </button>
      ))}
    </div>
  );
}

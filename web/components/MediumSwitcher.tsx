"use client";

import { useRouter } from "next/navigation";

// Extracted out of SiteHeader (which is rendered from both server and
// client trees and can't itself hold interactive state without a wider
// refactor - see SiteHeader.tsx's doc comment) so that constraint holds
// everywhere except the two medium-specific workspaces that actually
// need this control. Writes the visited medium to localStorage so a
// future visit to "/" can skip the chooser and go straight there - see
// app/page.tsx once that read/redirect side lands; this component only
// owns the write + the switch itself, not the read.
const STORAGE_KEY = "aura-last-medium";

export function MediumSwitcher({
  active,
  forceDark,
}: {
  active: "music" | "webtoons";
  forceDark?: boolean;
}) {
  const router = useRouter();

  function go(next: "music" | "webtoons") {
    if (next === active) return;
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Storage unavailable (private browsing, quota) - the switch itself
      // still works, it just won't be remembered next visit.
    }
    router.push(next === "music" ? "/music" : "/comics");
  }

  const border = forceDark ? "border-white/10" : "border-black/[0.08] dark:border-white/[0.08]";
  const activeClass = forceDark ? "bg-white/10 text-white/90" : "bg-black/[0.05] text-ink dark:bg-white/10 dark:text-ink-dark";
  const inactiveClass = forceDark
    ? "text-white/40 hover:text-white/70"
    : "text-ink/40 hover:text-ink/70 dark:text-ink-dark/40 dark:hover:text-ink-dark/70";

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

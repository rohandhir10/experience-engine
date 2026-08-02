import type { ReactNode } from "react";
import Link from "next/link";
import { Logo } from "./Logo";

const NAV_LINK =
  "text-[13px] text-ink/45 transition hover:text-ink/70 dark:text-ink-dark/45 dark:hover:text-ink-dark/70";

/** Shared across every page so navigation is consistent instead of each
 * page hand-rolling its own header. `active` hides that page's own link
 * from its own nav (no "Compare" link while already on /compare).
 * `right` is for page-specific controls (Result screen's Original toggle,
 * share button, etc.) rendered after the shared nav links.
 */
export function SiteHeader({
  active,
  right,
}: {
  active?: "compare" | "home";
  right?: ReactNode;
}) {
  return (
    <div className="mx-auto flex max-w-3xl items-center justify-between border-b border-black/[0.05] pb-5 dark:border-white/[0.05]">
      <Link href="/">
        <Logo />
      </Link>
      <div className="flex items-center gap-5 sm:gap-6">
        {active !== "compare" && (
          <Link href="/compare" className={NAV_LINK}>
            Compare
          </Link>
        )}
        {right}
      </div>
    </div>
  );
}

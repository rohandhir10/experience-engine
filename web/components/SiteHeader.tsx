import type { ReactNode } from "react";
import Link from "next/link";
import { Logo } from "./Logo";
import { MediumSwitcher } from "./MediumSwitcher";
import { ThemeToggle } from "./ThemeToggle";
import { UseCasesMenu } from "./UseCasesMenu";
import { MobileNavMenu } from "./MobileNavMenu";

/** Sign In / Get Started render everywhere (consistent global chrome, like
 * ChatGPT). Sign In is now real (Auth.js + Google, see web/auth.ts) and
 * always points at /sign-in, which renders the signed-in state itself
 * (dashboard link + sign out) rather than this header branching on it —
 * this component is rendered from BOTH server and client trees
 * (InputScreen.tsx is "use client"), so it can't read the session here
 * without a broader refactor. Pricing/Get Started are still cosmetic:
 * checkout runs through Paddle once a live account exists, but nothing
 * is charged today (see /pricing's own disclosure).
 *
 * active="music"/"webtoons" (set by /music and /comics respectively)
 * additionally renders MediumSwitcher - a small extracted client
 * component, for the same reason Sign In can't branch on session here:
 * SiteHeader itself stays server-renderable everywhere else, and only
 * the two pages that need an interactive switch pull in the client
 * bit. "/" and every other page pass neither and get no switcher.
 * UseCasesMenu and MobileNavMenu are the same pattern, for the same
 * reason - both need open/close state SiteHeader itself can't hold. */
export function SiteHeader({
  active,
  right,
  forceDark,
  minimal,
}: {
  active?: "pricing" | "home" | "music" | "webtoons";
  right?: ReactNode;
  forceDark?: boolean;
  // Drops Use Cases / Pricing / API from the row for pages that already
  // pack their own controls into `right` (currently just ResultScreen's
  // share-result screens) - those pages aren't marketing surfaces
  // someone's browsing from, and the full nav plus a page's own toolbar
  // together were enough items to force "Use Cases"/"Sign In" onto two
  // lines even at a 1280px desktop width, not just on mobile.
  minimal?: boolean;
}) {
  const dim = forceDark ? "text-white/65 hover:text-white/80" : "text-ink/65 hover:text-ink/78 dark:text-ink-dark/65 dark:hover:text-ink-dark/78";
  const navLink = `text-[13px] transition ${dim}`;

  return (
    <div
      className={
        forceDark
          ? "mx-auto flex w-full max-w-5xl items-center justify-between"
          : "mx-auto flex w-full max-w-3xl items-center justify-between border-b border-black/[0.09] pb-5 dark:border-white/[0.09]"
      }
    >
      <Link href="/">
        <Logo force={forceDark ? "light" : undefined} />
      </Link>
      <div className="flex flex-wrap items-center justify-end gap-y-2 gap-x-4 sm:gap-x-6">
        {(active === "music" || active === "webtoons") && (
          <MediumSwitcher active={active} forceDark={forceDark} />
        )}
        {!minimal && <UseCasesMenu forceDark={forceDark} />}
        {!minimal && active !== "pricing" && (
          <Link href="/pricing" className={`hidden sm:inline ${navLink}`}>
            Pricing
          </Link>
        )}
        {/* server/main.py's /v1/* routes are real (keys managed on
            /dashboard/settings, documented at /docs/api). The "Beta" pill
            that used to sit here is gone (real feedback that it read as
            visual clutter across the nav/tiles/sidebar) - the underlying
            gap it disclosed (no async job/poll pattern yet for API
            callers) is still real and still stated in prose on
            /docs/api itself, just not flagged with a badge in the nav.
            Points at the docs page rather than straight to key
            management - a visitor clicking "API" wants to know what it
            does first. */}
        {!minimal && (
          <Link
            href="/docs/api"
            className={`hidden items-center gap-1.5 text-[13px] transition sm:inline-flex ${
              forceDark ? "text-white/38 hover:text-white/68" : "text-ink/45 hover:text-ink/70 dark:text-ink-dark/45 dark:hover:text-ink-dark/70"
            }`}
          >
            API
          </Link>
        )}

        {right}

        <ThemeToggle forceDark={forceDark} />

        <Link href="/sign-in" className={`hidden sm:inline ${navLink}`}>
          Sign In
        </Link>
        <MobileNavMenu active={active} forceDark={forceDark} />
        <Link
          // Real bug this fixes: this used to hardcode /music#lyrics
          // everywhere, including on /comics (active="webtoons") - a
          // webtoons visitor clicking "Get Started" was silently sent
          // to the music tool instead. On webtoons, the upload area is
          // already the first thing on the page, so this just points
          // back at it rather than away from it.
          href={active === "webtoons" ? "/comics" : "/music#lyrics"}
          className={
            forceDark
              ? "whitespace-nowrap rounded-full bg-white px-4 py-1.5 text-[13px] font-medium text-black transition active:scale-[0.97]"
              : "whitespace-nowrap rounded-full bg-ink px-4 py-1.5 text-[13px] font-medium text-paper transition active:scale-[0.97] dark:bg-ink-dark dark:text-paper-dark"
          }
        >
          Get Started
        </Link>
      </div>
    </div>
  );
}

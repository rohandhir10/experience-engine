import type { ReactNode } from "react";
import Link from "next/link";
import { Logo } from "./Logo";

/** Sign In / Get Started render everywhere (consistent global chrome, like
 * ChatGPT). Sign In is now real (Auth.js + Google, see web/auth.ts) and
 * always points at /sign-in, which renders the signed-in state itself
 * (dashboard link + sign out) rather than this header branching on it —
 * this component is rendered from BOTH server and client trees
 * (InputScreen.tsx is "use client"), so it can't read the session here
 * without a broader refactor. Pricing/Get Started are still cosmetic:
 * there's no Stripe. */
export function SiteHeader({
  active,
  right,
  forceDark,
}: {
  active?: "compare" | "pricing" | "home";
  right?: ReactNode;
  forceDark?: boolean;
}) {
  const dim = forceDark ? "text-white/45 hover:text-white/75" : "text-ink/45 hover:text-ink/70 dark:text-ink-dark/45 dark:hover:text-ink-dark/70";
  const navLink = `text-[13px] transition ${dim}`;

  return (
    <div
      className={
        forceDark
          ? "mx-auto flex w-full max-w-5xl items-center justify-between"
          : "mx-auto flex w-full max-w-3xl items-center justify-between border-b border-black/[0.05] pb-5 dark:border-white/[0.05]"
      }
    >
      <Link href="/">
        <Logo force={forceDark ? "light" : undefined} />
      </Link>
      <div className="flex items-center gap-4 sm:gap-6">
        {active !== "compare" && (
          <Link href="/compare" className={`hidden sm:inline ${navLink}`}>
            Examples
          </Link>
        )}
        {active !== "pricing" && (
          <Link href="/pricing" className={`hidden sm:inline ${navLink}`}>
            Pricing
          </Link>
        )}
        <span
          className={`hidden items-center gap-1.5 text-[13px] sm:inline-flex ${
            forceDark ? "text-white/25" : "text-ink/30 dark:text-ink-dark/30"
          }`}
        >
          API
          <span
            className={`rounded-full px-1.5 py-0.5 text-[10px] uppercase tracking-wide ${
              forceDark
                ? "bg-white/10 text-white/40"
                : "bg-black/[0.05] text-ink/35 dark:bg-white/10 dark:text-ink-dark/40"
            }`}
          >
            Soon
          </span>
        </span>

        {right}

        <Link href="/sign-in" className={`hidden sm:inline ${navLink}`}>
          Sign In
        </Link>
        <Link
          href="/#lyrics"
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

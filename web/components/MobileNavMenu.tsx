"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import Link from "next/link";
import { USE_CASES } from "./UseCasesMenu";

// The real gap this fixes: every nav link below sm (Use Cases, Pricing,
// API, Sign In) carries `hidden sm:inline` with no mobile fallback at
// all - a visitor under 640px could only ever reach "Get Started". This
// is the hamburger + dropdown panel that was simply missing. Same
// client-component-extraction reasoning as MediumSwitcher/ThemeToggle/
// UseCasesMenu (SiteHeader.tsx's doc comment): needs open/close state,
// SiteHeader itself stays server-renderable.
export function MobileNavMenu({
  active,
  forceDark,
}: {
  active?: "pricing" | "home" | "music" | "webtoons";
  forceDark?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const iconColor = forceDark ? "text-white/78" : "text-ink/78 dark:text-ink-dark/78";
  const panel = forceDark
    ? "border-white/10 bg-[#161210]"
    : "border-black/[0.12] bg-paper dark:border-white/[0.12] dark:bg-paper-dark";
  const item = forceDark
    ? "text-white/80 hover:bg-white/[0.06]"
    : "text-ink/80 hover:bg-black/[0.03] dark:text-ink-dark/80 dark:hover:bg-white/[0.05]";
  const divider = forceDark ? "border-white/10" : "border-black/[0.10] dark:border-white/[0.11]";

  function close() {
    setOpen(false);
  }

  return (
    <div ref={ref} className="relative sm:hidden">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label={open ? "Close menu" : "Open menu"}
        aria-expanded={open}
        className={`grid h-8 w-8 place-items-center transition ${iconColor}`}
      >
        {open ? (
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" aria-hidden="true">
            <path d="M6 6l12 12M18 6L6 18" />
          </svg>
        ) : (
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" aria-hidden="true">
            <path d="M4 7h16M4 12h16M4 17h16" />
          </svg>
        )}
      </button>

      {open && (
        // `fixed`, not `absolute right-0` - this button isn't the
        // rightmost element in the header (Get Started renders after
        // it), so anchoring to the BUTTON's right edge pushed a 288px
        // panel off the left side of narrow viewports instead of
        // anchoring to the actual screen edge. Fixed positioning off
        // the real viewport edge is correct regardless of where the
        // button itself sits in the row.
        <div className={`fixed right-4 top-16 z-30 w-72 max-w-[calc(100vw-2rem)] rounded-xl border p-2 shadow-lg ${panel}`}>
          <nav className="flex flex-col gap-0.5 text-[14px]">
            <MobileLink href="/music" onClick={close} className={item} current={active === "music"}>
              Music
            </MobileLink>
            <MobileLink href="/comics" onClick={close} className={item} current={active === "webtoons"}>
              Webtoons
            </MobileLink>
            <div className={`my-1.5 border-t ${divider}`} />
            {USE_CASES.map((uc) => (
              <MobileLink key={uc.href} href={uc.href} onClick={close} className={item}>
                {uc.label}
              </MobileLink>
            ))}
            <div className={`my-1.5 border-t ${divider}`} />
            <MobileLink href="/how-it-works" onClick={close} className={item}>How it works</MobileLink>
            <MobileLink href="/pricing" onClick={close} className={item} current={active === "pricing"}>Pricing</MobileLink>
            <MobileLink href="/faq" onClick={close} className={item}>FAQ</MobileLink>
            <MobileLink href="/docs/api" onClick={close} className={item}>API</MobileLink>
            <div className={`my-1.5 border-t ${divider}`} />
            <MobileLink href="/sign-in" onClick={close} className={item}>Sign In</MobileLink>
          </nav>
        </div>
      )}
    </div>
  );
}

function MobileLink({
  href,
  onClick,
  className,
  current,
  children,
}: {
  href: string;
  onClick: () => void;
  className: string;
  current?: boolean;
  children: ReactNode;
}) {
  return (
    <Link
      href={href}
      onClick={onClick}
      className={`rounded-lg px-3 py-2.5 transition ${className} ${current ? "font-medium" : ""}`}
    >
      {children}
    </Link>
  );
}

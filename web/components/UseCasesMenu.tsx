"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";

// Fixes a real mislabeling bug: this nav item used to be a plain Link
// straight to /music#features (a section on the music tool, not "use
// cases" at all), while the two real use-case landing pages
// (app/lyrics-translation, app/manga-webtoon-translation) had no nav
// entry anywhere - reachable only by direct URL or search. Extracted as
// its own client component for the same reason MediumSwitcher/
// ThemeToggle are (SiteHeader.tsx's doc comment): it needs open/close
// state, and SiteHeader itself has to stay server-renderable everywhere.
export const USE_CASES = [
  { href: "/lyrics-translation", label: "Song lyric translation" },
  { href: "/manga-webtoon-translation", label: "Manga & webtoon translation" },
];

export function UseCasesMenu({ forceDark }: { forceDark?: boolean }) {
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

  const dim = forceDark
    ? "text-white/45 hover:text-white/75"
    : "text-ink/45 hover:text-ink/70 dark:text-ink-dark/45 dark:hover:text-ink-dark/70";
  const panel = forceDark
    ? "border-white/10 bg-[#161210]"
    : "border-black/[0.12] bg-paper dark:border-white/[0.12] dark:bg-paper-dark";
  const item = forceDark
    ? "text-white/70 hover:bg-white/[0.06]"
    : "text-ink/70 hover:bg-black/[0.03] dark:text-ink-dark/70 dark:hover:bg-white/[0.05]";

  return (
    <div ref={ref} className="relative hidden sm:block">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-haspopup="menu"
        className={`flex items-center gap-1 text-[13px] transition ${dim}`}
      >
        Use Cases
        <svg
          viewBox="0 0 24 24"
          width="10"
          height="10"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className={`transition ${open ? "rotate-180" : ""}`}
          aria-hidden="true"
        >
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>
      {open && (
        <div
          role="menu"
          className={`absolute left-0 top-full z-20 mt-2 w-64 rounded-xl border p-1.5 shadow-lg ${panel}`}
        >
          {USE_CASES.map((uc) => (
            <Link
              key={uc.href}
              href={uc.href}
              role="menuitem"
              onClick={() => setOpen(false)}
              className={`block rounded-lg px-3 py-2 text-[13px] transition ${item}`}
            >
              {uc.label}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

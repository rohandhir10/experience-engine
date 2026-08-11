"use client";

import { useEffect, useState } from "react";
import { applyTheme, readStoredTheme, writeStoredTheme, type Theme } from "@/lib/theme";

// Not rendered on forceDark pages (SiteHeader.tsx) - /music and /comics
// are a deliberate always-dark design (hardcoded white/black classes,
// no dark: variant to toggle away from), not something this overrides.
//
// `mounted` guards the icon only: app/layout.tsx's inline script already
// sets the real `dark` class on <html> before hydration, so there's no
// flash of the wrong THEME - but server-rendered HTML has no way to know
// which icon matches it, so the button would otherwise hydrate-mismatch
// or briefly show the wrong icon. Rendering a neutral placeholder until
// mount sidesteps both.
export function ThemeToggle({ forceDark }: { forceDark?: boolean }) {
  const [mounted, setMounted] = useState(false);
  const [theme, setTheme] = useState<Theme>("light");

  useEffect(() => {
    const current = readStoredTheme() ?? (document.documentElement.classList.contains("dark") ? "dark" : "light");
    setTheme(current);
    setMounted(true);
  }, []);

  if (forceDark) return null;

  function toggle() {
    const next: Theme = theme === "dark" ? "light" : "dark";
    setTheme(next);
    applyTheme(next);
    writeStoredTheme(next);
  }

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={mounted ? `Switch to ${theme === "dark" ? "light" : "dark"} mode` : "Toggle theme"}
      className="grid h-7 w-7 place-items-center rounded-full text-ink/75 transition hover:text-ink/78 dark:text-ink-dark/75 dark:hover:text-ink-dark/78"
    >
      {mounted && theme === "dark" ? (
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="4.5" />
          <path d="M12 2.5v2M12 19.5v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M2.5 12h2M19.5 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4" />
        </svg>
      ) : (
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
          <path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a7 7 0 0 0 10.5 10.5Z" />
        </svg>
      )}
    </button>
  );
}

export type Theme = "light" | "dark";

const STORAGE_KEY = "castia-theme";

// Client-side only, same reasoning as lib/mediumPreference.ts: a
// display preference, not account data worth round-tripping through
// server/accounts.py.
export function readStoredTheme(): Theme | null {
  try {
    const value = localStorage.getItem(STORAGE_KEY);
    return value === "light" || value === "dark" ? value : null;
  } catch {
    return null;
  }
}

export function writeStoredTheme(theme: Theme): void {
  try {
    localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    // Storage unavailable (private browsing, quota) - the toggle still
    // applies to the current page, it just won't be remembered.
  }
}

export function applyTheme(theme: Theme): void {
  document.documentElement.classList.toggle("dark", theme === "dark");
  document.documentElement.style.colorScheme = theme;
}

// Inlined into app/layout.tsx via next/script(strategy="beforeInteractive")
// rather than imported, so it runs before first paint with no dependency
// on React having hydrated yet - the whole point is avoiding a flash of
// the wrong theme. Must stay parseable as a bare, standalone script (no
// imports, no JSX) since Next inlines it as literal text.
export const THEME_INIT_SCRIPT = `
(function () {
  try {
    var stored = localStorage.getItem("${STORAGE_KEY}");
    var theme = stored === "light" || stored === "dark"
      ? stored
      : (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    document.documentElement.classList.toggle("dark", theme === "dark");
    document.documentElement.style.colorScheme = theme;
  } catch (e) {}
})();
`;

export type Medium = "music" | "webtoons";

const STORAGE_KEY = "aura-last-medium";

// Client-side only, deliberately not synced to the account (server/
// accounts.py owns user rows; web/auth.ts's own doc comment explains why
// Auth.js carries no database adapter here) - this is a low-stakes UX
// nicety, not data worth persisting server-side or across devices.
export function readMediumPreference(): Medium | null {
  try {
    const value = localStorage.getItem(STORAGE_KEY);
    return value === "music" || value === "webtoons" ? value : null;
  } catch {
    return null;
  }
}

export function writeMediumPreference(medium: Medium): void {
  try {
    localStorage.setItem(STORAGE_KEY, medium);
  } catch {
    // Storage unavailable (private browsing, quota) - the current
    // navigation still works, it just won't be remembered next visit.
  }
}

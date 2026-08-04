import type { HistoryEntry } from "./history";

/** The one piece of real per-row logic components/RecentAdaptations.tsx
 * needs to get right for a mixed music/webtoons history list: which
 * share page a row links to, and what to call it when there's no hook
 * line (every webtoons entry, since the comics wire shape never
 * produces one). Extracted into lib/ so it's covered by this harness's
 * pure-logic Vitest suite rather than only exercised by eye in the
 * browser. */
export function resolveHistoryEntryDisplay(
  entry: Pick<HistoryEntry, "resultId" | "medium" | "hook">
): { label: string; href: string } {
  const label =
    entry.hook || (entry.medium === "webtoons" ? "Adapted chapter" : "Untitled adaptation");
  const href =
    entry.medium === "webtoons" ? `/comics/s/${entry.resultId}` : `/s/${entry.resultId}`;
  return { label, href };
}

export type HistoryEntry = {
  resultId: string;
  createdAt: string;
  isFavorite: boolean;
  hook: string | null;
  sourceLanguage: string | null;
  targetLanguage: string | null;
};

/** Pure list transform behind the favorite star (components/
 * RecentAdaptations.tsx). Extracted from the component so the three
 * cases that actually matter — optimistic flip, rollback after a failed
 * write, and dropping a row that no longer belongs on the Favorites
 * page — are testable without a DOM.
 *
 * `dropWhenUnfavorited` is true on the Favorites page only: unstarring a
 * row there means it no longer belongs in the list at all, so it leaves
 * rather than sitting as a hollow star in a list of favorites. On the
 * dashboard's full history the same row stays put, just unstarred.
 */
export function applyFavorite(
  entries: HistoryEntry[],
  resultId: string,
  isFavorite: boolean,
  dropWhenUnfavorited = false
): HistoryEntry[] {
  if (dropWhenUnfavorited && !isFavorite) {
    return entries.filter((entry) => entry.resultId !== resultId);
  }
  return entries.map((entry) =>
    entry.resultId === resultId ? { ...entry, isFavorite } : entry
  );
}

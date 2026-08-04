import type { HistoryEntry } from "./history";

export type Collection = {
  id: string;
  name: string;
  count: number;
  createdAt?: string;
};

/** Pure list transforms behind components/CollectionsManager.tsx.
 * Extracted from the component for the same reason as lib/favorites.ts:
 * these are the parts with real edge cases (keeping counts honest after
 * an optimistic membership toggle, not letting a count go negative),
 * and they're worth testing without a DOM. */

export function renameIn(
  collections: Collection[],
  id: string,
  name: string
): Collection[] {
  return collections.map((c) => (c.id === id ? { ...c, name } : c));
}

export function removeFrom(collections: Collection[], id: string): Collection[] {
  return collections.filter((c) => c.id !== id);
}

/** Newest-first, matching the server's ordering, so an optimistically
 * added collection appears exactly where a refetch would put it. */
export function prepend(collections: Collection[], created: Collection): Collection[] {
  return [created, ...collections];
}

/** Keeps a collection's member count in step with an optimistic
 * membership toggle. Clamped at zero: a count that goes negative would
 * be a visible lie about state we only *think* we know, and the next
 * refetch would silently correct it — better to never render it. */
export function adjustCount(
  collections: Collection[],
  id: string,
  delta: number
): Collection[] {
  return collections.map((c) =>
    c.id === id ? { ...c, count: Math.max(0, c.count + delta) } : c
  );
}

/** Toggles one adaptation's membership in one collection, inside a
 * history list. Used by the "add to collection" menu in
 * components/RecentAdaptations.tsx, which renders its checkmarks from
 * each entry's own collectionIds.
 *
 * Adding is deduped so a double-click can't produce a duplicate id that
 * would then need two removes to clear. */
export function applyMembership(
  entries: HistoryEntry[],
  resultId: string,
  collectionId: string,
  member: boolean
): HistoryEntry[] {
  return entries.map((entry) => {
    if (entry.resultId !== resultId) return entry;
    const without = entry.collectionIds.filter((id) => id !== collectionId);
    return {
      ...entry,
      collectionIds: member ? [...without, collectionId] : without,
    };
  });
}

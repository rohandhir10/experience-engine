/** One row of a user's adaptation history, as returned by
 * /api/me/adaptations (server/accounts.py::list_adaptations). Lives in
 * its own module because favorites, collections, and the list component
 * all need it — it outgrew being a favorites-only type. */
export type HistoryEntry = {
  resultId: string;
  createdAt: string;
  isFavorite: boolean;
  /** "music" | "webtoons" (server/db_models.py::Adaptation.medium).
   * Drives which share page a row links to and how it renders, since a
   * webtoons entry has no hook line at all - see
   * components/RecentAdaptations.tsx. */
  medium: "music" | "webtoons";
  hook: string | null;
  sourceLanguage: string | null;
  targetLanguage: string | null;
  /** Ids of the collections this adaptation is filed into. Carried on
   * the listing so the "add to collection" menu opens already knowing
   * its own state instead of firing a request per row. */
  collectionIds: string[];
};

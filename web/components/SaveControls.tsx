"use client";

import { useEffect, useState } from "react";
import type { Collection } from "@/lib/collections";

/** Star + "file into a collection" for the result page (/s/[id]).
 *
 * The result page differs from the dashboard history list in one way
 * that drives this whole component: the song being viewed may not be in
 * the viewer's history at all — someone else's shared link, or their own
 * from before they signed in. Favorites and collections both hang off a
 * history row, so the first save-type action here creates one
 * (/api/me/adaptations/[id]/save) before the real write.
 *
 * That save deliberately happens on ACTION, never on page view: opening
 * a link someone sent you is not a decision to keep it.
 *
 * Renders nothing at all when signed out or when the account endpoints
 * aren't configured — an inert star on a public share page would be
 * worse than no star. */
export function SaveControls({ resultId }: { resultId: string }) {
  const [ready, setReady] = useState(false);
  const [available, setAvailable] = useState(false);
  const [isFavorite, setIsFavorite] = useState(false);
  const [collectionIds, setCollectionIds] = useState<string[]>([]);
  const [collections, setCollections] = useState<Collection[]>([]);
  const [menuOpen, setMenuOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      fetch(`/api/me/adaptations/${resultId}`).then((r) =>
        r.ok ? r.json() : null
      ),
      fetch("/api/me/collections").then((r) => (r.ok ? r.json() : null)),
    ])
      .then(([entry, collectionsBody]) => {
        if (cancelled) return;
        // A 401/503 from either (signed out, or accounts unconfigured)
        // leaves `available` false and the whole component invisible.
        if (entry === null) return;
        setAvailable(true);
        if (entry.adaptation) {
          setIsFavorite(Boolean(entry.adaptation.isFavorite));
          setCollectionIds(entry.adaptation.collectionIds ?? []);
        }
        if (collectionsBody?.collections) setCollections(collectionsBody.collections);
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setReady(true);
      });
    return () => {
      cancelled = true;
    };
  }, [resultId]);

  /** Creates the history row if this result isn't in it yet. Every
   * save-type action funnels through here first, so the caller never has
   * to know whether it's dealing with an own-adaptation or a shared
   * link. */
  async function ensureSaved(): Promise<boolean> {
    const res = await fetch(`/api/me/adaptations/${resultId}/save`, {
      method: "POST",
    }).catch(() => null);
    return Boolean(res?.ok);
  }

  async function toggleFavorite() {
    if (busy) return;
    const next = !isFavorite;
    setIsFavorite(next);
    setBusy(true);
    try {
      if (!(await ensureSaved())) throw new Error("save failed");
      const res = await fetch(`/api/me/adaptations/${resultId}/favorite`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ isFavorite: next }),
      });
      if (!res.ok) throw new Error(String(res.status));
    } catch {
      setIsFavorite(!next);
    } finally {
      setBusy(false);
    }
  }

  async function toggleCollection(collectionId: string, member: boolean) {
    const before = collectionIds;
    setCollectionIds(
      member
        ? [...before.filter((id) => id !== collectionId), collectionId]
        : before.filter((id) => id !== collectionId)
    );
    try {
      if (!(await ensureSaved())) throw new Error("save failed");
      const res = await fetch(
        `/api/me/collections/${collectionId}/adaptations/${resultId}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ member }),
        }
      );
      if (!res.ok) throw new Error(String(res.status));
    } catch {
      setCollectionIds(before);
    }
  }

  if (!ready || !available) return null;

  return (
    <div className="flex items-center gap-3">
      <button
        type="button"
        onClick={toggleFavorite}
        disabled={busy}
        aria-pressed={isFavorite}
        aria-label={isFavorite ? "Remove from favorites" : "Save to favorites"}
        className={`rounded-full p-1 transition disabled:opacity-40 ${
          isFavorite
            ? "text-accent"
            : "text-ink/30 hover:text-ink/60 dark:text-ink-dark/30 dark:hover:text-ink-dark/60"
        }`}
      >
        <svg
          viewBox="0 0 24 24"
          className="h-4 w-4"
          fill={isFavorite ? "currentColor" : "none"}
          stroke="currentColor"
          strokeWidth={1.6}
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M12 3.5l2.6 5.3 5.9.85-4.25 4.15 1 5.85L12 16.9l-5.25 2.75 1-5.85L3.5 9.65l5.9-.85z" />
        </svg>
      </button>

      {collections.length > 0 && (
        <div className="relative">
          <button
            type="button"
            onClick={() => setMenuOpen((v) => !v)}
            aria-expanded={menuOpen}
            className="text-[13px] text-ink/45 transition hover:text-ink/70 dark:text-ink-dark/45 dark:hover:text-ink-dark/70"
          >
            {collectionIds.length > 0 ? `In ${collectionIds.length}` : "Save to…"}
          </button>
          {menuOpen && (
            <>
              <div
                className="fixed inset-0 z-10"
                onClick={() => setMenuOpen(false)}
                aria-hidden="true"
              />
              <div className="absolute right-0 top-full z-20 mt-1 max-h-64 w-56 overflow-y-auto rounded-xl border border-black/[0.08] bg-paper p-1 shadow-lg dark:border-white/[0.08] dark:bg-[#1b1b1d]">
                {collections.map((collection) => {
                  const member = collectionIds.includes(collection.id);
                  return (
                    <button
                      key={collection.id}
                      type="button"
                      onClick={() => toggleCollection(collection.id, !member)}
                      className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-left text-[13px] text-ink/70 transition hover:bg-black/[0.04] dark:text-ink-dark/70 dark:hover:bg-white/[0.06]"
                    >
                      <span
                        className={`w-3 shrink-0 text-[11px] ${
                          member ? "text-accent" : "text-transparent"
                        }`}
                        aria-hidden="true"
                      >
                        ✓
                      </span>
                      <span className="min-w-0 truncate">{collection.name}</span>
                    </button>
                  );
                })}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

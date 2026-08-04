"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { applyFavorite } from "@/lib/favorites";
import { applyMembership, type Collection } from "@/lib/collections";
import type { HistoryEntry } from "@/lib/history";

type HistoryState =
  | { status: "loading" }
  | { status: "signed-out" }
  | { status: "error" }
  | { status: "ready"; entries: HistoryEntry[] };

function StarIcon({ filled }: { filled: boolean }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className="h-4 w-4"
      fill={filled ? "currentColor" : "none"}
      stroke="currentColor"
      strokeWidth={1.6}
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12 3.5l2.6 5.3 5.9.85-4.25 4.15 1 5.85L12 16.9l-5.25 2.75 1-5.85L3.5 9.65l5.9-.85z" />
    </svg>
  );
}

/** The signed-in user's adaptation history, backed by
 * /api/me/adaptations (which returns signedIn:false rather than an error
 * for anonymous visitors — history is an account perk, not a
 * requirement). Each entry links to the same shareable /s/[id] page the
 * original submission landed on.
 *
 * favoritesOnly drives both the query and the empty-state copy, so the
 * dashboard's "Recent" list and the Favorites page are the same
 * component rather than two that can drift apart. */
export function RecentAdaptations({
  favoritesOnly = false,
}: {
  favoritesOnly?: boolean;
}) {
  const [state, setState] = useState<HistoryState>({ status: "loading" });
  const [pending, setPending] = useState<Set<string>>(new Set());
  const [collections, setCollections] = useState<Collection[]>([]);
  const [openMenuFor, setOpenMenuFor] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const query = favoritesOnly ? "?favoritesOnly=true" : "";
    fetch(`/api/me/adaptations${query}`)
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error(String(res.status)))))
      .then((body) => {
        if (cancelled) return;
        if (!body.signedIn) setState({ status: "signed-out" });
        else setState({ status: "ready", entries: body.adaptations ?? [] });
      })
      .catch(() => {
        if (!cancelled) setState({ status: "error" });
      });
    return () => {
      cancelled = true;
    };
  }, [favoritesOnly]);

  // Collections for the per-row "file into…" menu. Failing to load them
  // only costs the menu — the list itself and favoriting still work, so
  // this deliberately has no error state of its own.
  useEffect(() => {
    let cancelled = false;
    fetch("/api/me/collections")
      .then((res) => (res.ok ? res.json() : null))
      .then((body) => {
        if (!cancelled && body?.collections) setCollections(body.collections);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const toggleMembership = useCallback(
    async (entry: HistoryEntry, collectionId: string, member: boolean) => {
      const update = (value: boolean) =>
        setState((prev) =>
          prev.status === "ready"
            ? {
                status: "ready",
                entries: applyMembership(
                  prev.entries,
                  entry.resultId,
                  collectionId,
                  value
                ),
              }
            : prev
        );
      update(member);
      try {
        const res = await fetch(
          `/api/me/collections/${collectionId}/adaptations/${entry.resultId}`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ member }),
          }
        );
        if (!res.ok) throw new Error(String(res.status));
        setCollections((prev) =>
          prev.map((c) =>
            c.id === collectionId
              ? { ...c, count: Math.max(0, c.count + (member ? 1 : -1)) }
              : c
          )
        );
      } catch {
        update(!member);
      }
    },
    []
  );

  const toggleFavorite = useCallback(
    async (entry: HistoryEntry) => {
      const next = !entry.isFavorite;
      const update = (isFavorite: boolean, dropWhenUnfavorited = false) =>
        setState((prev) =>
          prev.status === "ready"
            ? {
                status: "ready",
                entries: applyFavorite(
                  prev.entries,
                  entry.resultId,
                  isFavorite,
                  dropWhenUnfavorited
                ),
              }
            : prev
        );

      // Optimistic: flip immediately, roll back if the write fails. A
      // star that lags a round-trip feels broken; a star that flips back
      // with an error is at least truthful about what happened. The row
      // isn't dropped from the Favorites page until the write actually
      // succeeds — a failed unstar should leave it visible to retry.
      update(next);
      setPending((prev) => new Set(prev).add(entry.resultId));
      try {
        const res = await fetch(`/api/me/adaptations/${entry.resultId}/favorite`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ isFavorite: next }),
        });
        if (!res.ok) throw new Error(String(res.status));
        if (favoritesOnly && !next) update(next, true);
      } catch {
        update(!next);
      } finally {
        setPending((prev) => {
          const copy = new Set(prev);
          copy.delete(entry.resultId);
          return copy;
        });
      }
    },
    [favoritesOnly]
  );

  if (state.status === "loading") {
    return <p className="mt-4 text-[14px] text-ink/30 dark:text-ink-dark/30">Loading…</p>;
  }
  if (state.status === "signed-out") {
    return (
      <p className="mt-4 text-[14px] leading-relaxed text-ink/40 dark:text-ink-dark/40">
        <Link
          href="/sign-in"
          className="underline decoration-ink/20 underline-offset-4 hover:text-ink/70 dark:decoration-ink-dark/20 dark:hover:text-ink-dark/70"
        >
          Sign in
        </Link>{" "}
        to keep {favoritesOnly ? "favorites" : "a history of the songs you adapt"}.
      </p>
    );
  }
  if (state.status === "error") {
    return (
      <p className="mt-4 text-[14px] text-ink/40 dark:text-ink-dark/40">
        Couldn't load your {favoritesOnly ? "favorites" : "history"} right now — your
        adaptations are still saved.
      </p>
    );
  }
  if (state.entries.length === 0) {
    return (
      <p className="mt-4 text-[14px] leading-relaxed text-ink/40 dark:text-ink-dark/40">
        {favoritesOnly
          ? "No favorites yet — star an adaptation to keep it here."
          : "No adaptations yet — the first song you adapt will show up here."}
      </p>
    );
  }
  return (
    <ul className="mt-4 divide-y divide-black/[0.05] dark:divide-white/[0.05]">
      {state.entries.map((entry) => (
        <li key={entry.resultId} className="flex items-center gap-3 py-3">
          <button
            type="button"
            onClick={() => toggleFavorite(entry)}
            disabled={pending.has(entry.resultId)}
            aria-pressed={entry.isFavorite}
            aria-label={
              entry.isFavorite
                ? `Remove ${entry.hook || "this adaptation"} from favorites`
                : `Add ${entry.hook || "this adaptation"} to favorites`
            }
            className={`shrink-0 rounded-full p-1 transition disabled:opacity-40 ${
              entry.isFavorite
                ? "text-accent"
                : "text-ink/20 hover:text-ink/45 dark:text-ink-dark/20 dark:hover:text-ink-dark/45"
            }`}
          >
            <StarIcon filled={entry.isFavorite} />
          </button>
          <Link
            href={`/s/${entry.resultId}`}
            className="group flex min-w-0 flex-1 items-baseline justify-between gap-4"
          >
            <span className="min-w-0 truncate text-[14px] text-ink/75 transition group-hover:text-ink dark:text-ink-dark/75 dark:group-hover:text-ink-dark">
              {entry.hook || "Untitled adaptation"}
            </span>
            <span className="shrink-0 text-[12px] text-ink/35 dark:text-ink-dark/35">
              {[entry.sourceLanguage, entry.targetLanguage].filter(Boolean).join(" → ")}
              {" · "}
              {new Date(entry.createdAt).toLocaleDateString()}
            </span>
          </Link>

          {collections.length > 0 && (
            <div className="relative shrink-0">
              <button
                type="button"
                onClick={() =>
                  setOpenMenuFor((prev) => (prev === entry.resultId ? null : entry.resultId))
                }
                aria-expanded={openMenuFor === entry.resultId}
                aria-label={`Add ${entry.hook || "this adaptation"} to a collection`}
                className={`rounded-full px-2 py-1 text-[12px] transition ${
                  entry.collectionIds.length > 0
                    ? "text-ink/55 dark:text-ink-dark/55"
                    : "text-ink/30 hover:text-ink/60 dark:text-ink-dark/30 dark:hover:text-ink-dark/60"
                }`}
              >
                {entry.collectionIds.length > 0
                  ? `In ${entry.collectionIds.length}`
                  : "Add to…"}
              </button>

              {openMenuFor === entry.resultId && (
                <>
                  {/* Click-away layer: a menu you can only close by
                      re-clicking the same button reads as stuck. */}
                  <div
                    className="fixed inset-0 z-10"
                    onClick={() => setOpenMenuFor(null)}
                    aria-hidden="true"
                  />
                  <div className="absolute right-0 top-full z-20 mt-1 max-h-64 w-56 overflow-y-auto rounded-xl border border-black/[0.08] bg-paper p-1 shadow-lg dark:border-white/[0.08] dark:bg-[#1b1b1d]">
                    {collections.map((collection) => {
                      const member = entry.collectionIds.includes(collection.id);
                      return (
                        <button
                          key={collection.id}
                          type="button"
                          onClick={() => toggleMembership(entry, collection.id, !member)}
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
        </li>
      ))}
    </ul>
  );
}

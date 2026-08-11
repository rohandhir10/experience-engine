"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { applyFavorite } from "@/lib/favorites";
import { applyMembership, type Collection } from "@/lib/collections";
import { CollectionMenu } from "./CollectionMenu";
import type { HistoryEntry } from "@/lib/history";
import { resolveHistoryEntryDisplay } from "@/lib/historyEntryDisplay";

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
 * requirement). Each entry links to whichever share page its own medium
 * uses — /s/[id] for music, /comics/s/[id] for webtoons — since this
 * combined list can now genuinely contain both (see
 * server/accounts.py::list_adaptations's medium=None default).
 *
 * favoritesOnly drives both the query and the empty-state copy, so the
 * dashboard's "Recent" list and the Favorites page are the same
 * component rather than two that can drift apart. `medium`, when
 * passed, narrows to just that one — omitted (the default, and what
 * every caller passes today), both mediums show together in one
 * timeline, no filter control exists yet to change that. */
export function RecentAdaptations({
  favoritesOnly = false,
  medium,
}: {
  favoritesOnly?: boolean;
  medium?: "music" | "webtoons";
}) {
  const [state, setState] = useState<HistoryState>({ status: "loading" });
  const [pending, setPending] = useState<Set<string>>(new Set());
  const [collections, setCollections] = useState<Collection[]>([]);

  useEffect(() => {
    let cancelled = false;
    const query = new URLSearchParams();
    if (favoritesOnly) query.set("favoritesOnly", "true");
    if (medium) query.set("medium", medium);
    const qs = query.toString();
    fetch(`/api/me/adaptations${qs ? `?${qs}` : ""}`)
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
  }, [favoritesOnly, medium]);

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
    return <p className="mt-4 text-[14px] text-ink/45 dark:text-ink-dark/45">Loading…</p>;
  }
  if (state.status === "signed-out") {
    return (
      <p className="mt-4 text-[14px] leading-relaxed text-ink/62 dark:text-ink-dark/62">
        <Link
          href="/sign-in"
          className="underline decoration-ink/20 underline-offset-4 hover:text-ink/78 dark:decoration-ink-dark/20 dark:hover:text-ink-dark/78"
        >
          Sign in
        </Link>{" "}
        to keep {favoritesOnly ? "favorites" : "a history of what you adapt"}.
      </p>
    );
  }
  if (state.status === "error") {
    return (
      <p className="mt-4 text-[14px] text-ink/62 dark:text-ink-dark/62">
        Couldn't load your {favoritesOnly ? "favorites" : "history"} right now — your
        adaptations are still saved.
      </p>
    );
  }
  if (state.entries.length === 0) {
    return (
      <div className="mt-4 flex flex-col items-center gap-2.5 rounded-2xl border border-dashed border-black/[0.13] px-6 py-10 text-center dark:border-white/[0.14]">
        <span className="flex h-9 w-9 items-center justify-center rounded-full bg-black/[0.04] text-ink/40 dark:bg-white/[0.06] dark:text-ink-dark/40">
          <StarIcon filled={false} />
        </span>
        <p className="text-[14px] leading-relaxed text-ink/62 dark:text-ink-dark/62">
          {favoritesOnly
            ? "No favorites yet — star an adaptation to keep it here."
            : "No adaptations yet — the first thing you adapt will show up here."}
        </p>
      </div>
    );
  }
  return (
    <ul className="mt-4 divide-y divide-black/[0.09] dark:divide-white/[0.09]">
      {state.entries.map((entry) => {
        const { label, href } = resolveHistoryEntryDisplay(entry);
        return (
          <li key={entry.resultId} className="flex items-center gap-3 py-3">
            <button
              type="button"
              onClick={() => toggleFavorite(entry)}
              disabled={pending.has(entry.resultId)}
              aria-pressed={entry.isFavorite}
              aria-label={
                entry.isFavorite ? `Remove ${label} from favorites` : `Add ${label} to favorites`
              }
              className={`shrink-0 rounded-full p-1 transition disabled:opacity-40 ${
                entry.isFavorite
                  ? "text-accent"
                  : "text-ink/32 hover:text-ink/65 dark:text-ink-dark/32 dark:hover:text-ink-dark/65"
              }`}
            >
              <StarIcon filled={entry.isFavorite} />
            </button>
            <Link
              href={href}
              className="group flex min-w-0 flex-1 items-baseline justify-between gap-4"
            >
              <span className="min-w-0 truncate text-[14px] text-ink/80 transition group-hover:text-ink dark:text-ink-dark/80 dark:group-hover:text-ink-dark">
                {label}
              </span>
              <span className="shrink-0 text-[12px] text-ink/50 dark:text-ink-dark/50">
                {[entry.sourceLanguage, entry.targetLanguage].filter(Boolean).join(" → ")}
                {" · "}
                {new Date(entry.createdAt).toLocaleDateString()}
              </span>
            </Link>

            <CollectionMenu
              collections={collections}
              memberIds={entry.collectionIds}
              onToggle={(collectionId, member) =>
                toggleMembership(entry, collectionId, member)
              }
              onCollectionCreated={(created) =>
                setCollections((prev) => [created, ...prev])
              }
              ariaLabel={`Add ${label} to a collection`}
            />
          </li>
        );
      })}
    </ul>
  );
}

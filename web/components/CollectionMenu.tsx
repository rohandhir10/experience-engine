"use client";

import { useState } from "react";
import type { Collection } from "@/lib/collections";

/** The "file this song into a collection" popover, shared by the
 * dashboard history list (RecentAdaptations) and the result page
 * (SaveControls) — it was about to be a third near-identical copy of the
 * same markup.
 *
 * Owns its own trigger button, click-away layer, and inline "new
 * collection" form. Creating from here immediately files the song into
 * what it just made: the whole reason to create a collection at this
 * moment is the song in front of you, so making the user create it and
 * then click it again would be busywork.
 *
 * Deliberately still rendered when the user has NO collections yet —
 * that's precisely when they most need to make one, and an earlier
 * version hid the menu in exactly that case, which made the feature
 * undiscoverable on first use. */
export function CollectionMenu({
  collections,
  memberIds,
  onToggle,
  onCollectionCreated,
  emptyLabel = "Add to…",
  ariaLabel = "Add to a collection",
}: {
  collections: Collection[];
  memberIds: string[];
  onToggle: (collectionId: string, member: boolean) => void | Promise<void>;
  onCollectionCreated: (collection: Collection) => void;
  emptyLabel?: string;
  ariaLabel?: string;
}) {
  const [open, setOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);

  function close() {
    setOpen(false);
    setCreating(false);
    setNewName("");
    setFailed(false);
  }

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault();
    const name = newName.trim();
    if (!name || busy) return;
    setBusy(true);
    setFailed(false);
    try {
      const res = await fetch("/api/me/collections", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      if (!res.ok) throw new Error(String(res.status));
      const created: Collection = await res.json();
      onCollectionCreated({ ...created, count: 0 });
      // File the song into it right away — that's why they made it.
      await onToggle(created.id, true);
      close();
    } catch {
      // Keep the typed name and the form open so it can be retried
      // rather than silently losing what they wrote.
      setFailed(true);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="relative shrink-0">
      <button
        type="button"
        onClick={() => (open ? close() : setOpen(true))}
        aria-expanded={open}
        aria-label={ariaLabel}
        className={`rounded-full px-2 py-1 text-[12px] transition ${
          memberIds.length > 0
            ? "text-ink/70 dark:text-ink-dark/70"
            : "text-ink/45 hover:text-ink/72 dark:text-ink-dark/45 dark:hover:text-ink-dark/72"
        }`}
      >
        {memberIds.length > 0 ? `In ${memberIds.length}` : emptyLabel}
      </button>

      {open && (
        <>
          {/* Click-away layer: a menu you can only close by re-clicking
              the same button reads as stuck. */}
          <div className="fixed inset-0 z-10" onClick={close} aria-hidden="true" />
          <div className="absolute right-0 top-full z-20 mt-1 max-h-72 w-60 overflow-y-auto rounded-xl border border-black/[0.12] bg-paper p-1 shadow-lg dark:border-white/[0.12] dark:bg-[#1b1b1d]">
            {collections.map((collection) => {
              const member = memberIds.includes(collection.id);
              return (
                <button
                  key={collection.id}
                  type="button"
                  onClick={() => onToggle(collection.id, !member)}
                  className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-left text-[13px] text-ink/78 transition hover:bg-black/[0.04] dark:text-ink-dark/78 dark:hover:bg-white/[0.06]"
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

            {collections.length > 0 && (
              <div className="my-1 border-t border-black/[0.10] dark:border-white/[0.12]" />
            )}

            {creating ? (
              <form onSubmit={handleCreate} className="p-1">
                <input
                  autoFocus
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Escape") {
                      setCreating(false);
                      setNewName("");
                    }
                  }}
                  placeholder="Collection name…"
                  maxLength={100}
                  disabled={busy}
                  className="w-full rounded-lg border border-black/[0.12] bg-white/70 px-2.5 py-1.5 text-[13px] text-ink outline-none transition placeholder:text-ink/45 focus:border-black/20 disabled:opacity-50 dark:border-white/[0.12] dark:bg-white/[0.04] dark:text-ink-dark dark:placeholder:text-ink-dark/45"
                />
                {failed && (
                  <p role="alert" className="mt-1 px-1 text-[11px] text-red-500/80">
                    Couldn't create that — try again.
                  </p>
                )}
                <button
                  type="submit"
                  disabled={!newName.trim() || busy}
                  className="mt-1.5 w-full rounded-lg bg-ink px-2.5 py-1.5 text-[12px] font-medium text-paper transition disabled:opacity-30 dark:bg-ink-dark dark:text-paper-dark"
                >
                  {busy ? "Creating…" : "Create and add"}
                </button>
              </form>
            ) : (
              <button
                type="button"
                onClick={() => setCreating(true)}
                className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-left text-[13px] text-ink/68 transition hover:bg-black/[0.04] dark:text-ink-dark/68 dark:hover:bg-white/[0.06]"
              >
                <span className="w-3 shrink-0 text-[13px]" aria-hidden="true">
                  +
                </span>
                <span>New collection</span>
              </button>
            )}
          </div>
        </>
      )}
    </div>
  );
}

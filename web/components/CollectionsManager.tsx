"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  adjustCount,
  prepend,
  removeFrom,
  renameIn,
  type Collection,
} from "@/lib/collections";
import type { HistoryEntry } from "@/lib/history";

type LoadState =
  | { status: "loading" }
  | { status: "signed-out" }
  | { status: "error" }
  | { status: "ready"; collections: Collection[] };

/** Collections: create, rename, delete, and file adaptations into them.
 *
 * Ownership of both sides of every membership write is enforced upstream
 * (server/accounts.py::set_collection_membership needs the collection
 * AND the adaptation to belong to the caller), so this component never
 * reasons about permissions — a failed write just rolls back. */
export function CollectionsManager() {
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);
  const [selected, setSelected] = useState<Collection | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/me/collections")
      .then(async (res) => {
        if (res.status === 401) return { signedOut: true as const };
        if (!res.ok) throw new Error(String(res.status));
        return res.json();
      })
      .then((body) => {
        if (cancelled) return;
        if (body.signedOut) setState({ status: "signed-out" });
        else setState({ status: "ready", collections: body.collections ?? [] });
      })
      .catch(() => {
        if (!cancelled) setState({ status: "error" });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const update = useCallback(
    (fn: (collections: Collection[]) => Collection[]) =>
      setState((prev) =>
        prev.status === "ready"
          ? { status: "ready", collections: fn(prev.collections) }
          : prev
      ),
    []
  );

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault();
    const name = newName.trim();
    if (!name || creating) return;
    setCreating(true);
    try {
      const res = await fetch("/api/me/collections", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      if (!res.ok) throw new Error(String(res.status));
      const created: Collection = await res.json();
      // Not optimistic: the id comes from the server, and inventing a
      // placeholder id would make the row's own rename/delete buttons
      // target something that doesn't exist yet.
      update((collections) => prepend(collections, { ...created, count: 0 }));
      setNewName("");
    } catch {
      // Left in the input so the name isn't lost to a failed request.
    } finally {
      setCreating(false);
    }
  }

  async function handleRename(collection: Collection) {
    const next = window.prompt("Rename collection", collection.name)?.trim();
    if (!next || next === collection.name) return;
    update((collections) => renameIn(collections, collection.id, next));
    const res = await fetch(`/api/me/collections/${collection.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: next }),
    }).catch(() => null);
    if (!res?.ok) update((collections) => renameIn(collections, collection.id, collection.name));
  }

  async function handleDelete(collection: Collection) {
    if (
      !window.confirm(
        `Delete "${collection.name}"? The adaptations in it are kept — only the collection goes away.`
      )
    )
      return;
    update((collections) => removeFrom(collections, collection.id));
    if (selected?.id === collection.id) setSelected(null);
    const res = await fetch(`/api/me/collections/${collection.id}`, {
      method: "DELETE",
    }).catch(() => null);
    if (!res?.ok) update((collections) => prepend(collections, collection));
  }

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
        to group your adaptations into collections.
      </p>
    );
  }
  if (state.status === "error") {
    return (
      <p className="mt-4 text-[14px] text-ink/62 dark:text-ink-dark/62">
        Couldn't load your collections right now.
      </p>
    );
  }

  if (selected) {
    return (
      <CollectionDetail
        collection={selected}
        onBack={() => setSelected(null)}
        onCountChange={(delta) => {
          update((collections) => adjustCount(collections, selected.id, delta));
          setSelected((prev) =>
            prev ? { ...prev, count: Math.max(0, prev.count + delta) } : prev
          );
        }}
      />
    );
  }

  return (
    <>
      <form onSubmit={handleCreate} className="mt-5 flex max-w-md gap-2">
        <input
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="New collection name…"
          maxLength={100}
          className="min-w-0 flex-1 rounded-full border border-black/[0.12] bg-white/70 px-4 py-2 text-[14px] text-ink outline-none transition placeholder:text-ink/45 focus:border-black/20 dark:border-white/[0.12] dark:bg-white/[0.03] dark:text-ink-dark dark:placeholder:text-ink-dark/45"
        />
        <button
          type="submit"
          disabled={!newName.trim() || creating}
          className="shrink-0 rounded-full bg-ink px-5 py-2 text-[13px] font-medium text-paper transition active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-30 dark:bg-ink-dark dark:text-paper-dark"
        >
          Create
        </button>
      </form>

      {state.collections.length === 0 ? (
        <p className="mt-6 text-[14px] leading-relaxed text-ink/62 dark:text-ink-dark/62">
          No collections yet — make one above to start grouping your
          adaptations.
        </p>
      ) : (
        <ul className="mt-6 divide-y divide-black/[0.09] dark:divide-white/[0.09]">
          {state.collections.map((collection) => (
            <li key={collection.id} className="flex items-center gap-3 py-3">
              <button
                type="button"
                onClick={() => setSelected(collection)}
                className="min-w-0 flex-1 text-left"
              >
                <span className="block truncate text-[14px] text-ink/80 transition hover:text-ink dark:text-ink-dark/80 dark:hover:text-ink-dark">
                  {collection.name}
                </span>
                <span className="text-[12px] text-ink/50 dark:text-ink-dark/50">
                  {collection.count} {collection.count === 1 ? "song" : "songs"}
                </span>
              </button>
              <button
                type="button"
                onClick={() => handleRename(collection)}
                className="shrink-0 text-[12px] text-ink/62 underline decoration-ink/15 underline-offset-4 transition hover:text-ink/78 dark:text-ink-dark/62 dark:decoration-ink-dark/15 dark:hover:text-ink-dark/78"
              >
                Rename
              </button>
              <button
                type="button"
                onClick={() => handleDelete(collection)}
                className="shrink-0 text-[12px] text-red-500/60 underline decoration-red-500/20 underline-offset-4 transition hover:text-red-500/90"
              >
                Delete
              </button>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

/** One collection's contents, plus a picker for filing more of your
 * history into it. Loads both lists (members and full history) so the
 * picker can show what's already in — the engine has no "not in this
 * collection" query and adding one for a page-sized list would be
 * premature. */
function CollectionDetail({
  collection,
  onBack,
  onCountChange,
}: {
  collection: Collection;
  onBack: () => void;
  onCountChange: (delta: number) => void;
}) {
  const [members, setMembers] = useState<HistoryEntry[] | null>(null);
  const [history, setHistory] = useState<HistoryEntry[] | null>(null);
  const [pending, setPending] = useState<Set<string>>(new Set());
  const [showPicker, setShowPicker] = useState(false);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      fetch(`/api/me/adaptations?collectionId=${collection.id}`).then((r) => r.json()),
      fetch("/api/me/adaptations").then((r) => r.json()),
    ])
      .then(([inCollection, all]) => {
        if (cancelled) return;
        setMembers(inCollection.adaptations ?? []);
        setHistory(all.adaptations ?? []);
      })
      .catch(() => {
        if (cancelled) return;
        setMembers([]);
        setHistory([]);
      });
    return () => {
      cancelled = true;
    };
  }, [collection.id]);

  async function setMembership(entry: HistoryEntry, member: boolean) {
    setPending((prev) => new Set(prev).add(entry.resultId));
    const before = members ?? [];
    setMembers(
      member ? [entry, ...before] : before.filter((e) => e.resultId !== entry.resultId)
    );
    onCountChange(member ? 1 : -1);
    try {
      const res = await fetch(
        `/api/me/collections/${collection.id}/adaptations/${entry.resultId}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ member }),
        }
      );
      if (!res.ok) throw new Error(String(res.status));
    } catch {
      setMembers(before);
      onCountChange(member ? -1 : 1);
    } finally {
      setPending((prev) => {
        const copy = new Set(prev);
        copy.delete(entry.resultId);
        return copy;
      });
    }
  }

  const memberIds = new Set((members ?? []).map((e) => e.resultId));
  const addable = (history ?? []).filter((e) => !memberIds.has(e.resultId));

  return (
    <div className="mt-5">
      <button
        type="button"
        onClick={onBack}
        className="text-[13px] text-ink/65 underline decoration-ink/15 underline-offset-4 transition hover:text-ink/78 dark:text-ink-dark/65 dark:decoration-ink-dark/15 dark:hover:text-ink-dark/78"
      >
        ← All collections
      </button>

      <h2 className="mt-4 font-serif text-xl text-ink dark:text-ink-dark">
        {collection.name}
      </h2>

      {members === null ? (
        <p className="mt-4 text-[14px] text-ink/45 dark:text-ink-dark/45">Loading…</p>
      ) : members.length === 0 ? (
        <p className="mt-4 text-[14px] text-ink/62 dark:text-ink-dark/62">
          Nothing in this collection yet.
        </p>
      ) : (
        <ul className="mt-4 divide-y divide-black/[0.09] dark:divide-white/[0.09]">
          {members.map((entry) => (
            <li key={entry.resultId} className="flex items-center gap-3 py-3">
              <Link
                href={`/s/${entry.resultId}`}
                className="min-w-0 flex-1 truncate text-[14px] text-ink/80 transition hover:text-ink dark:text-ink-dark/80 dark:hover:text-ink-dark"
              >
                {entry.hook || "Untitled adaptation"}
              </Link>
              <button
                type="button"
                onClick={() => setMembership(entry, false)}
                disabled={pending.has(entry.resultId)}
                className="shrink-0 text-[12px] text-ink/62 underline decoration-ink/15 underline-offset-4 transition hover:text-ink/78 disabled:opacity-40 dark:text-ink-dark/62 dark:decoration-ink-dark/15 dark:hover:text-ink-dark/78"
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}

      {addable.length > 0 && (
        <div className="mt-8 border-t border-black/[0.09] pt-5 dark:border-white/[0.09]">
          <button
            type="button"
            onClick={() => setShowPicker((v) => !v)}
            className="text-[13px] text-ink/68 transition hover:text-ink/80 dark:text-ink-dark/68 dark:hover:text-ink-dark/80"
          >
            {showPicker ? "Hide" : "Add from your history"} ({addable.length})
          </button>
          {showPicker && (
            <ul className="mt-3 divide-y divide-black/[0.09] dark:divide-white/[0.09]">
              {addable.map((entry) => (
                <li key={entry.resultId} className="flex items-center gap-3 py-2.5">
                  <span className="min-w-0 flex-1 truncate text-[14px] text-ink/72 dark:text-ink-dark/72">
                    {entry.hook || "Untitled adaptation"}
                  </span>
                  <button
                    type="button"
                    onClick={() => setMembership(entry, true)}
                    disabled={pending.has(entry.resultId)}
                    className="shrink-0 rounded-full border border-black/10 px-3 py-1 text-[12px] text-ink/72 transition hover:text-ink disabled:opacity-40 dark:border-white/10 dark:text-ink-dark/72 dark:hover:text-ink-dark"
                  >
                    Add
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

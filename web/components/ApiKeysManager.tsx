"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import type { ApiKeyEntry, CreatedApiKey } from "@/lib/apiKeys";

type LoadState =
  | { status: "loading" }
  | { status: "signed-out" }
  | { status: "error" }
  | { status: "ready"; keys: ApiKeyEntry[] };

/** Public API key management (server/api_keys.py, the /v1/* endpoints).
 * A newly-created key's raw value is shown exactly once, right here,
 * with an explicit "won't be shown again" warning - the backend never
 * stores or returns it again after this response, same one-time-reveal
 * convention GitHub/Stripe use, so there is nothing to "look up later"
 * if it's lost; only revoking and creating a new one. */
export function ApiKeysManager() {
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);
  const [justCreated, setJustCreated] = useState<CreatedApiKey | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/me/api-keys")
      .then(async (res) => {
        if (res.status === 401) return { signedOut: true as const };
        if (!res.ok) throw new Error(String(res.status));
        return res.json();
      })
      .then((body) => {
        if (cancelled) return;
        if (body.signedOut) setState({ status: "signed-out" });
        else setState({ status: "ready", keys: body.apiKeys ?? [] });
      })
      .catch(() => {
        if (!cancelled) setState({ status: "error" });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function createKey() {
    const name = newName.trim();
    if (!name || creating) return;
    setCreating(true);
    setError(null);
    try {
      const res = await fetch("/api/me/api-keys", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(body.error || body.detail || "Couldn't create a key.");
      setJustCreated(body);
      setNewName("");
      setState((prev) =>
        prev.status === "ready" ? { status: "ready", keys: [body, ...prev.keys] } : prev
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Couldn't create a key.");
    } finally {
      setCreating(false);
    }
  }

  async function revokeKey(id: string) {
    const res = await fetch(`/api/me/api-keys/${id}`, { method: "DELETE" });
    if (!res.ok) return;
    setState((prev) =>
      prev.status === "ready"
        ? {
            status: "ready",
            keys: prev.keys.map((k) =>
              k.id === id ? { ...k, revokedAt: new Date().toISOString() } : k
            ),
          }
        : prev
    );
  }

  async function copyKey() {
    if (!justCreated) return;
    try {
      await navigator.clipboard.writeText(justCreated.key);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      // Clipboard access denied - the key is still visible to copy by hand.
    }
  }

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
        to create API keys.
      </p>
    );
  }
  if (state.status === "error") {
    return (
      <p className="mt-4 text-[14px] text-ink/40 dark:text-ink-dark/40">
        Couldn't load your API keys right now.
      </p>
    );
  }

  return (
    <div className="mt-6">
      {justCreated && (
        <div className="mb-6 rounded-xl border border-accent/30 bg-accent/[0.06] p-4">
          <p className="text-[13px] font-medium text-ink dark:text-ink-dark">
            "{justCreated.name}" created — copy this key now
          </p>
          <p className="mt-1 text-[12px] text-ink/50 dark:text-ink-dark/50">
            This is the only time the full key is shown. Store it somewhere safe.
          </p>
          <div className="mt-3 flex items-center gap-2">
            <code className="flex-1 truncate rounded-lg border border-black/[0.12] bg-white/70 px-3 py-2 text-[12px] text-ink dark:border-white/[0.12] dark:bg-white/[0.03] dark:text-ink-dark">
              {justCreated.key}
            </code>
            <button
              type="button"
              onClick={copyKey}
              className="shrink-0 rounded-full bg-ink px-4 py-2 text-[12px] font-medium text-paper transition active:scale-[0.97] dark:bg-ink-dark dark:text-paper-dark"
            >
              {copied ? "Copied" : "Copy"}
            </button>
          </div>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <input
          type="text"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") createKey();
          }}
          placeholder="e.g. Production"
          className="w-56 rounded-lg border border-black/[0.12] bg-white/70 px-3 py-2 text-[13px] text-ink placeholder:text-ink/30 transition dark:border-white/[0.12] dark:bg-white/[0.03] dark:text-ink-dark dark:placeholder:text-ink-dark/30"
        />
        <button
          type="button"
          onClick={createKey}
          disabled={!newName.trim() || creating}
          className="rounded-full bg-ink px-4 py-2 text-[13px] font-medium text-paper transition active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-40 dark:bg-ink-dark dark:text-paper-dark"
        >
          {creating ? "Creating…" : "New key"}
        </button>
      </div>
      {error && <p className="mt-2 text-[12px] text-red-500/80">{error}</p>}

      {state.keys.length === 0 ? (
        <p className="mt-6 text-[14px] leading-relaxed text-ink/40 dark:text-ink-dark/40">
          No API keys yet — create one to call the public API.
        </p>
      ) : (
        <ul className="mt-6 divide-y divide-black/[0.09] dark:divide-white/[0.09]">
          {state.keys.map((key) => (
            <li key={key.id} className="flex items-center justify-between gap-4 py-3">
              <div className="min-w-0">
                <p className="truncate text-[14px] text-ink/80 dark:text-ink-dark/80">
                  {key.name}{" "}
                  <span className="text-ink/35 dark:text-ink-dark/35">{key.prefix}…</span>
                </p>
                <p className="mt-0.5 text-[12px] text-ink/35 dark:text-ink-dark/35">
                  {key.revokedAt
                    ? `Revoked ${new Date(key.revokedAt).toLocaleDateString()}`
                    : key.lastUsedAt
                      ? `Last used ${new Date(key.lastUsedAt).toLocaleDateString()}`
                      : "Never used"}
                </p>
              </div>
              {!key.revokedAt && (
                <button
                  type="button"
                  onClick={() => revokeKey(key.id)}
                  className="shrink-0 text-[12px] text-red-500/70 transition hover:text-red-500"
                >
                  Revoke
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

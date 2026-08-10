"use client";

import { useState } from "react";
import { signOut, useSession } from "next-auth/react";

/** The two data rights web/app/privacy states as real practice, made
 * real: download everything this account holds, and delete the account
 * outright.
 *
 * Deletion is guarded by typing the account's own email rather than a
 * plain "are you sure" dialog. That isn't ceremony - it's the difference
 * between a misclick and a decision, for an action with no undo on the
 * other side (server/accounts.py::delete_account removes the row, the
 * history, the credit ledger and any cached result nobody else still
 * references). The button stays disabled until the typed value matches.
 *
 * Export downloads client-side from the JSON the proxy returns rather
 * than streaming a file from the engine: the payload is already JSON the
 * browser has in hand, and a Blob download needs no extra endpoint,
 * no temporary file and no storage that would then need its own
 * retention policy.
 */
export function AccountDataControls() {
  const { data: session } = useSession();
  const email = session?.user?.email ?? "";

  const [exporting, setExporting] = useState(false);
  const [confirmText, setConfirmText] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Case-insensitive and whitespace-trimmed: a capital letter from a
  // phone keyboard's autocapitalize is a typo, not a signal the person
  // didn't mean it.
  const confirmed =
    email.length > 0 && confirmText.trim().toLowerCase() === email.toLowerCase();

  async function handleExport() {
    setExporting(true);
    setError(null);
    try {
      const res = await fetch("/api/me/export");
      if (!res.ok) throw new Error(String(res.status));
      const data = await res.json();

      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `castia-account-data-${new Date().toISOString().slice(0, 10)}.json`;
      link.click();
      URL.revokeObjectURL(url);
    } catch {
      setError("Couldn't prepare your data export. Please try again.");
    } finally {
      setExporting(false);
    }
  }

  async function handleDelete() {
    if (!confirmed) return;
    setDeleting(true);
    setError(null);
    try {
      const res = await fetch("/api/me", { method: "DELETE" });
      if (!res.ok) throw new Error(String(res.status));
      // The account no longer exists, so the session is meaningless -
      // sign out rather than leaving a signed-in-looking UI pointed at
      // a deleted account.
      await signOut({ callbackUrl: "/" });
    } catch {
      setError("Couldn't delete your account. Please try again, or contact support.");
      setDeleting(false);
    }
  }

  return (
    <div className="mt-12">
      <h2 className="font-serif text-xl text-ink dark:text-ink-dark">Your data</h2>

      <div className="mt-4 rounded-xl border border-black/[0.08] p-4 dark:border-white/[0.08]">
        <p className="text-[14px] font-medium text-ink dark:text-ink-dark">
          Download your data
        </p>
        <p className="mt-1 max-w-prose text-[13px] leading-relaxed text-ink/45 dark:text-ink-dark/45">
          Everything on this account as a JSON file — your adaptations and their
          full adapted text, collections, credit history, and character bibles.
          API keys are listed by name only; the keys themselves were shown once at
          creation and aren&apos;t stored anywhere we could re-read them.
        </p>
        <button
          type="button"
          onClick={handleExport}
          disabled={exporting}
          className="mt-3 rounded-full border border-black/[0.1] px-5 py-2 text-[13px] font-medium text-ink/70 transition hover:border-black/20 hover:text-ink disabled:cursor-not-allowed disabled:opacity-50 dark:border-white/[0.12] dark:text-ink-dark/70 dark:hover:text-ink-dark"
        >
          {exporting ? "Preparing…" : "Download my data"}
        </button>
      </div>

      <div className="mt-4 rounded-xl border border-red-500/25 p-4">
        <p className="text-[14px] font-medium text-ink dark:text-ink-dark">
          Delete this account
        </p>
        <p className="mt-1 max-w-prose text-[13px] leading-relaxed text-ink/45 dark:text-ink-dark/45">
          Permanently removes your account, adaptation history, collections, API
          keys, credit history and character bibles. Any remaining credit balance
          is forfeited. This cannot be undone — download your data first if you
          want to keep it.
        </p>

        {email ? (
          <>
            <label className="mt-3 block text-[12px] text-ink/50 dark:text-ink-dark/50">
              Type <span className="font-medium text-ink/70 dark:text-ink-dark/70">{email}</span> to
              confirm
              <input
                type="text"
                value={confirmText}
                onChange={(e) => setConfirmText(e.target.value)}
                autoComplete="off"
                className="mt-1.5 w-full max-w-sm rounded-lg border border-black/[0.08] bg-white/70 px-3 py-2 text-[14px] text-ink transition dark:border-white/[0.08] dark:bg-white/[0.03] dark:text-ink-dark"
              />
            </label>
            <button
              type="button"
              onClick={handleDelete}
              disabled={!confirmed || deleting}
              className="mt-3 rounded-full bg-red-600 px-5 py-2 text-[13px] font-medium text-white transition active:scale-[0.97] disabled:cursor-not-allowed disabled:opacity-40"
            >
              {deleting ? "Deleting…" : "Delete my account"}
            </button>
          </>
        ) : (
          <p className="mt-3 text-[13px] text-ink/40 dark:text-ink-dark/40">
            Sign in to manage this account.
          </p>
        )}
      </div>

      {error && <p className="mt-3 text-[12px] text-red-600/80 dark:text-red-400/80">{error}</p>}
    </div>
  );
}

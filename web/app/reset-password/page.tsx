"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { SiteHeader } from "@/components/SiteHeader";

type Status = { kind: "form" } | { kind: "loading" } | { kind: "done" } | { kind: "error"; message: string };

/** Landed on from the link server/emailing.py sends (POST /api/auth/
 * forgot-password) - reads ?token= and submits it with a new password
 * against POST /api/auth/reset-password exactly once. A client
 * component for the same reason /verify-email/page.tsx is one: the
 * token is single-use, and this needs the raw token from the URL
 * client-side to submit it at all - a server-rendered page couldn't
 * spend it without exposing it in a form action first.
 *
 * Wrapped in Suspense (below) because useSearchParams opts a client
 * component out of static rendering - same reason /verify-email needs
 * the same wrapper. */
function ResetPasswordContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState<Status>({ kind: "form" });

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!token) {
      setStatus({ kind: "error", message: "This reset link is invalid or has expired." });
      return;
    }
    setStatus({ kind: "loading" });
    try {
      const res = await fetch("/api/auth/reset-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, password }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        setStatus({ kind: "error", message: body.detail ?? "This reset link is invalid or has expired." });
        return;
      }
      setStatus({ kind: "done" });
    } catch {
      setStatus({ kind: "error", message: "CASTIA is temporarily unreachable. Please try again in a few minutes." });
    }
  }

  return (
    <main className="min-h-screen px-6 pb-28 pt-8 sm:px-10">
      <div className="mx-auto max-w-3xl">
        <SiteHeader />
      </div>

      <div className="mx-auto mt-24 flex max-w-sm flex-col items-center text-center">
        {!token ? (
          <>
            <h1 className="font-serif text-2xl text-ink dark:text-ink-dark">
              That link isn't valid.
            </h1>
            <p className="mt-3 text-[14px] leading-relaxed text-ink/68 dark:text-ink-dark/68">
              It may have expired or already been used. You can request a
              fresh one.
            </p>
            <Link
              href="/forgot-password"
              className="mt-8 inline-flex w-full items-center justify-center rounded-full bg-ink px-6 py-3 text-[14px] font-medium text-paper transition active:scale-[0.97] dark:bg-ink-dark dark:text-paper-dark"
            >
              Request a new link
            </Link>
          </>
        ) : status.kind === "done" ? (
          <>
            <h1 className="font-serif text-2xl text-ink dark:text-ink-dark">Password updated.</h1>
            <p className="mt-3 text-[14px] leading-relaxed text-ink/68 dark:text-ink-dark/68">
              Sign in with your new password.
            </p>
            <Link
              href="/sign-in"
              className="mt-8 inline-flex w-full items-center justify-center rounded-full bg-ink px-6 py-3 text-[14px] font-medium text-paper transition active:scale-[0.97] dark:bg-ink-dark dark:text-paper-dark"
            >
              Sign in
            </Link>
          </>
        ) : (
          <>
            <h1 className="font-serif text-2xl text-ink dark:text-ink-dark">Choose a new password.</h1>

            <form onSubmit={handleSubmit} className="mt-8 w-full space-y-3 text-left">
              <div>
                <label htmlFor="password" className="text-[12px] text-ink/75 dark:text-ink-dark/75">
                  New password
                </label>
                <input
                  id="password"
                  type="password"
                  required
                  minLength={8}
                  autoComplete="new-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-black/10 bg-transparent px-3.5 py-2.5 text-[14px] text-ink outline-none focus:border-ink/30 dark:border-white/10 dark:text-ink-dark dark:focus:border-ink-dark/30"
                />
                <p className="mt-1 text-[12px] text-ink/68 dark:text-ink-dark/68">At least 8 characters.</p>
              </div>

              {status.kind === "error" && (
                <p className="text-[13px] text-red-600/80 dark:text-red-400/80">{status.message}</p>
              )}

              <button
                type="submit"
                disabled={status.kind === "loading"}
                className="w-full rounded-full bg-ink px-6 py-3 text-[14px] font-medium text-paper transition active:scale-[0.97] disabled:opacity-50 dark:bg-ink-dark dark:text-paper-dark"
              >
                {status.kind === "loading" ? "Updating…" : "Update password"}
              </button>
            </form>
          </>
        )}
      </div>
    </main>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={null}>
      <ResetPasswordContent />
    </Suspense>
  );
}

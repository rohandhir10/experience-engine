"use client";

import { useState } from "react";
import Link from "next/link";
import { SiteHeader } from "@/components/SiteHeader";

type Status = { kind: "idle" } | { kind: "loading" } | { kind: "sent" } | { kind: "error"; message: string };

/** Requests a password reset link for an email/password account -
 * mirrors SignUpForm.tsx's shape (client state, no page navigation of
 * its own). Always lands on the same "sent" state regardless of whether
 * the email exists, is Google-only, or was never registered - the
 * backend's no-account-enumeration rule (server/password_auth.py)
 * requires the response to be indistinguishable, so the UI can't show
 * anything more specific either without defeating that. */
export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<Status>({ kind: "idle" });

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus({ kind: "loading" });
    try {
      const res = await fetch("/api/auth/forgot-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      if (res.status === 429) {
        setStatus({ kind: "error", message: "Too many requests. Try again tomorrow." });
        return;
      }
      // Every other outcome (including a real backend error) still shows
      // "sent" - anything more specific would leak whether the email
      // exists, defeating the point of the no-enumeration response.
      setStatus({ kind: "sent" });
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
        {status.kind === "sent" ? (
          <>
            <h1 className="font-serif text-2xl text-ink dark:text-ink-dark">Check your email.</h1>
            <p className="mt-3 text-[14px] leading-relaxed text-ink/68 dark:text-ink-dark/68">
              If an account exists for <strong className="text-ink/80 dark:text-ink-dark/80">{email}</strong>,
              we sent a link to reset its password. It expires in 1 hour.
            </p>
            <Link
              href="/sign-in"
              className="mt-8 inline-flex w-full items-center justify-center rounded-full border border-black/10 px-6 py-3 text-[14px] text-ink/72 transition hover:text-ink dark:border-white/10 dark:text-ink-dark/72 dark:hover:text-ink-dark"
            >
              Back to sign in
            </Link>
          </>
        ) : (
          <>
            <h1 className="font-serif text-2xl text-ink dark:text-ink-dark">Reset your password.</h1>
            <p className="mt-3 text-[14px] leading-relaxed text-ink/68 dark:text-ink-dark/68">
              Enter the email on your account and we'll send you a link to
              choose a new password.
            </p>

            <form onSubmit={handleSubmit} className="mt-8 w-full space-y-3 text-left">
              <div>
                <label htmlFor="email" className="text-[12px] text-ink/75 dark:text-ink-dark/75">
                  Email
                </label>
                <input
                  id="email"
                  type="email"
                  required
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-black/10 bg-transparent px-3.5 py-2.5 text-[14px] text-ink outline-none focus:border-ink/30 dark:border-white/10 dark:text-ink-dark dark:focus:border-ink-dark/30"
                />
              </div>

              {status.kind === "error" && (
                <p className="text-[13px] text-red-600/80 dark:text-red-400/80">{status.message}</p>
              )}

              <button
                type="submit"
                disabled={status.kind === "loading"}
                className="w-full rounded-full bg-ink px-6 py-3 text-[14px] font-medium text-paper transition active:scale-[0.97] disabled:opacity-50 dark:bg-ink-dark dark:text-paper-dark"
              >
                {status.kind === "loading" ? "Sending…" : "Send reset link"}
              </button>
            </form>

            <p className="mt-6 text-[13px] text-ink/75 dark:text-ink-dark/75">
              <Link href="/sign-in" className="underline decoration-ink/20 underline-offset-4">
                Back to sign in
              </Link>
            </p>
          </>
        )}
      </div>
    </main>
  );
}

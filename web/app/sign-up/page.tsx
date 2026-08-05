"use client";

import { useState } from "react";
import Link from "next/link";
import { SiteHeader } from "@/components/SiteHeader";

type Status = { kind: "idle" } | { kind: "loading" } | { kind: "sent"; email: string } | { kind: "error"; message: string };

/** Email/password sign-up (server/password_auth.py). A client component,
 * unlike /sign-in's server-component + server-action shape, because the
 * interesting states here (submitting, "check your email", resend) are
 * all post-submit UI feedback with no page navigation of their own -
 * verification happens on a *different* page (/verify-email) once the
 * link is actually clicked. */
export default function SignUpPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState<Status>({ kind: "idle" });

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus({ kind: "loading" });
    try {
      const res = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        setStatus({ kind: "error", message: body.error ?? "Couldn't create that account. Try again." });
        return;
      }
      setStatus({ kind: "sent", email });
    } catch {
      setStatus({ kind: "error", message: "CASTIA is temporarily unreachable. Please try again in a few minutes." });
    }
  }

  async function handleResend() {
    if (status.kind !== "sent") return;
    await fetch("/api/auth/resend-verification", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: status.email }),
    }).catch(() => {});
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
            <p className="mt-3 text-[14px] leading-relaxed text-ink/50 dark:text-ink-dark/50">
              We sent a verification link to <strong className="text-ink/80 dark:text-ink-dark/80">{status.email}</strong>.
              Click it to activate your account, then come back and sign in.
            </p>
            <button
              type="button"
              onClick={handleResend}
              className="mt-8 w-full rounded-full border border-black/10 px-6 py-3 text-[14px] text-ink/60 transition hover:text-ink dark:border-white/10 dark:text-ink-dark/60 dark:hover:text-ink-dark"
            >
              Resend the link
            </button>
          </>
        ) : (
          <>
            <h1 className="font-serif text-2xl text-ink dark:text-ink-dark">Create an account.</h1>
            <p className="mt-3 text-[14px] leading-relaxed text-ink/50 dark:text-ink-dark/50">
              You don't need one to use CASTIA — sign up to keep a history of
              every song you adapt, on any device.
            </p>

            <form onSubmit={handleSubmit} className="mt-8 w-full space-y-3 text-left">
              <div>
                <label htmlFor="email" className="text-[12px] text-ink/45 dark:text-ink-dark/45">
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
              <div>
                <label htmlFor="password" className="text-[12px] text-ink/45 dark:text-ink-dark/45">
                  Password
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
                <p className="mt-1 text-[12px] text-ink/35 dark:text-ink-dark/35">At least 8 characters.</p>
              </div>

              {status.kind === "error" && (
                <p className="text-[13px] text-red-600/80 dark:text-red-400/80">{status.message}</p>
              )}

              <button
                type="submit"
                disabled={status.kind === "loading"}
                className="w-full rounded-full bg-ink px-6 py-3 text-[14px] font-medium text-paper transition active:scale-[0.97] disabled:opacity-50 dark:bg-ink-dark dark:text-paper-dark"
              >
                {status.kind === "loading" ? "Creating account…" : "Create account"}
              </button>
            </form>

            <p className="mt-6 text-[13px] text-ink/45 dark:text-ink-dark/45">
              Already have an account?{" "}
              <Link href="/sign-in" className="underline decoration-ink/20 underline-offset-4">
                Sign in
              </Link>
            </p>
          </>
        )}

        <Link
          href="/music#lyrics"
          className="mt-6 text-[13px] text-ink/45 underline decoration-ink/15 underline-offset-4 transition hover:text-ink/70 dark:text-ink-dark/45 dark:decoration-ink-dark/15 dark:hover:text-ink-dark/70"
        >
          Just take me to CASTIA →
        </Link>
      </div>
    </main>
  );
}

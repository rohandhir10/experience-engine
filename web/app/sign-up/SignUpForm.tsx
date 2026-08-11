"use client";

import { useState } from "react";
import Link from "next/link";

type Status = { kind: "idle" } | { kind: "loading" } | { kind: "sent"; email: string } | { kind: "error"; message: string };

/** The interactive email/password half of /sign-up - split out of the
 * page itself so the page can stay a server component (needed to read
 * process.env.AUTH_GOOGLE_ID and call the "use server" signIn("google")
 * action, same shape /sign-in already uses) while this still gets the
 * client-side state (submitting, "check your email", resend) that has
 * no page navigation of its own - verification happens on a *different*
 * page (/verify-email) once the link is actually clicked.
 *
 * `googleSignUp` is a Server Action passed down as a prop (a supported
 * Next.js App Router pattern - it's a reference, not a closure this
 * component executes) - undefined when Google isn't configured, same
 * "don't render a button that can't work" rule /sign-in's own
 * `googleConfigured` check already follows. */
export function SignUpForm({
  googleConfigured,
  googleSignUp,
}: {
  googleConfigured: boolean;
  googleSignUp?: () => Promise<void>;
}) {
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

  if (status.kind === "sent") {
    return (
      <>
        <h1 className="font-serif text-2xl text-ink dark:text-ink-dark">Check your email.</h1>
        <p className="mt-3 text-[14px] leading-relaxed text-ink/68 dark:text-ink-dark/68">
          We sent a verification link to <strong className="text-ink/80 dark:text-ink-dark/80">{status.email}</strong>.
          Click it to activate your account, then come back and sign in.
        </p>
        <button
          type="button"
          onClick={handleResend}
          className="mt-8 w-full rounded-full border border-black/10 px-6 py-3 text-[14px] text-ink/72 transition hover:text-ink dark:border-white/10 dark:text-ink-dark/72 dark:hover:text-ink-dark"
        >
          Resend the link
        </button>
      </>
    );
  }

  return (
    <>
      <h1 className="font-serif text-2xl text-ink dark:text-ink-dark">Create an account.</h1>
      <p className="mt-3 text-[14px] leading-relaxed text-ink/68 dark:text-ink-dark/68">
        You don't need one to use CASTIA — sign up to keep a history of
        every song you adapt, on any device.
      </p>

      {/* Same "Continue with Google" path /sign-in already offers - this
          used to be sign-in-only, so a visitor who landed on /sign-up
          directly (rather than clicking through from /sign-in) had no
          fast path at all, only email/password, with no visible sign a
          quicker option existed elsewhere. Google sign-in upserts the
          account on first use, so this genuinely IS the sign-up flow for
          that path, not a redirect to a different feature. */}
      {googleConfigured && googleSignUp && (
        <form action={googleSignUp} className="mt-8 w-full">
          <button
            type="submit"
            className="inline-flex w-full items-center justify-center gap-3 rounded-full bg-ink px-6 py-3 text-[14px] font-medium text-paper transition active:scale-[0.97] dark:bg-ink-dark dark:text-paper-dark"
          >
            Continue with Google
          </button>
        </form>
      )}

      {googleConfigured && googleSignUp && (
        <div className="mt-6 flex w-full items-center gap-3 text-[12px] text-ink/65 dark:text-ink-dark/65">
          <div className="h-px flex-1 bg-black/[0.08] dark:bg-white/[0.08]" />
          or
          <div className="h-px flex-1 bg-black/[0.08] dark:bg-white/[0.08]" />
        </div>
      )}

      <form
        onSubmit={handleSubmit}
        className={`w-full space-y-3 text-left ${googleConfigured && googleSignUp ? "mt-6" : "mt-8"}`}
      >
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
        <div>
          <label htmlFor="password" className="text-[12px] text-ink/75 dark:text-ink-dark/75">
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
          {status.kind === "loading" ? "Creating account…" : "Create account"}
        </button>
      </form>

      <p className="mt-6 text-[13px] text-ink/75 dark:text-ink-dark/75">
        Already have an account?{" "}
        <Link href="/sign-in" className="underline decoration-ink/20 underline-offset-4">
          Sign in
        </Link>
      </p>
    </>
  );
}

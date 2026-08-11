"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { SiteHeader } from "@/components/SiteHeader";

type Status = "checking" | "ok" | "error";

/** Landed on from the link server/emailing.py logs (real sending isn't
 * wired up yet - see that module) - reads ?token=, spends it against
 * POST /api/auth/verify-email exactly once. A client component because
 * the token is single-use: this has to run the check itself rather than
 * something a server-rendered page could just assert from the URL.
 *
 * Wrapped in Suspense (below) because useSearchParams opts a client
 * component out of static rendering - Next.js requires a boundary so the
 * rest of the page doesn't have to. */
function VerifyEmailContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [status, setStatus] = useState<Status>("checking");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      return;
    }
    let cancelled = false;
    fetch("/api/auth/verify-email", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token }),
    })
      .then((res) => {
        if (!cancelled) setStatus(res.ok ? "ok" : "error");
      })
      .catch(() => {
        if (!cancelled) setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  return (
    <main className="min-h-screen px-6 pb-28 pt-8 sm:px-10">
      <div className="mx-auto max-w-3xl">
        <SiteHeader />
      </div>

      <div className="mx-auto mt-24 flex max-w-sm flex-col items-center text-center">
        {status === "checking" && (
          <p className="text-[14px] text-ink/68 dark:text-ink-dark/68">Verifying…</p>
        )}
        {status === "ok" && (
          <>
            <h1 className="font-serif text-2xl text-ink dark:text-ink-dark">Email verified.</h1>
            <p className="mt-3 text-[14px] leading-relaxed text-ink/68 dark:text-ink-dark/68">
              Your account is active. Sign in to start keeping a history of
              what you adapt.
            </p>
            <Link
              href="/sign-in"
              className="mt-8 inline-flex w-full items-center justify-center rounded-full bg-ink px-6 py-3 text-[14px] font-medium text-paper transition active:scale-[0.97] dark:bg-ink-dark dark:text-paper-dark"
            >
              Sign in
            </Link>
          </>
        )}
        {status === "error" && (
          <>
            <h1 className="font-serif text-2xl text-ink dark:text-ink-dark">
              That link isn't valid.
            </h1>
            <p className="mt-3 text-[14px] leading-relaxed text-ink/68 dark:text-ink-dark/68">
              It may have expired or already been used. You can request a
              fresh one from the sign-up page.
            </p>
            <Link
              href="/sign-up"
              className="mt-8 inline-flex w-full items-center justify-center rounded-full bg-ink px-6 py-3 text-[14px] font-medium text-paper transition active:scale-[0.97] dark:bg-ink-dark dark:text-paper-dark"
            >
              Back to sign up
            </Link>
          </>
        )}
      </div>
    </main>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={null}>
      <VerifyEmailContent />
    </Suspense>
  );
}

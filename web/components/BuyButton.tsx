"use client";

import { useState } from "react";
import { signIn, useSession } from "next-auth/react";
import { isPaddleConfigured, openCheckout } from "@/lib/paddle";

/** The actual checkout trigger for a pricing-page tier - real Paddle.js
 * wiring (lib/paddle.ts), not a static "Coming soon" label, but genuinely
 * inert until `priceId` and the client-side Paddle env vars exist: there
 * is no live Paddle account behind this yet (see docs/CAPABILITY_MATRIX.md),
 * so every path below degrades to a clear message instead of a broken
 * checkout call. Requires sign-in first - Paddle needs a user_id to
 * attach the resulting transaction to (customData, read back by
 * server/paddle.py's webhook handler), and there's no anonymous-then-
 * attach-later flow for that. */
export function BuyButton({
  priceId,
  label,
  className,
}: {
  priceId: string | undefined;
  label: string;
  className?: string;
}) {
  const { data: session, status } = useSession();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleClick() {
    setError(null);
    if (!priceId || !isPaddleConfigured()) {
      setError("Checkout isn't live yet - this price hasn't been set up.");
      return;
    }
    if (status === "unauthenticated") {
      void signIn("google");
      return;
    }
    if (!session?.castiaUserId) {
      setError("Still signing you in - try again in a moment.");
      return;
    }
    setLoading(true);
    try {
      await openCheckout(priceId, session.castiaUserId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not open checkout.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <button
        type="button"
        onClick={handleClick}
        disabled={loading}
        className={
          className ??
          "rounded-full bg-ink px-5 py-2 text-[13px] font-medium text-paper transition active:scale-[0.97] disabled:opacity-50 dark:bg-ink-dark dark:text-paper-dark"
        }
      >
        {loading ? "Opening checkout…" : label}
      </button>
      {error && (
        <p className="mt-2 text-[12px] leading-relaxed text-red-600/80 dark:text-red-400/80">
          {error}
        </p>
      )}
    </div>
  );
}

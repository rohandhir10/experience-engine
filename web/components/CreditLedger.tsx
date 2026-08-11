"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import type { CreditsResponse, CreditTransaction } from "@/lib/credits";

type LoadState =
  | { status: "loading" }
  | { status: "signed-out" }
  | { status: "error" }
  | { status: "ready"; data: CreditsResponse };

const REASON_LABELS: Record<CreditTransaction["reason"], string> = {
  purchase: "Credit pack purchase",
  subscription_renewal: "Subscription renewal",
  adaptation: "Adaptation",
  refund: "Refund",
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function useCredits(): LoadState {
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    fetch("/api/me/credits")
      .then(async (res) => {
        if (res.status === 401) return { signedOut: true as const };
        if (!res.ok) throw new Error(String(res.status));
        return res.json();
      })
      .then((body) => {
        if (cancelled) return;
        if (body.signedOut) setState({ status: "signed-out" });
        else setState({ status: "ready", data: body });
      })
      .catch(() => {
        if (!cancelled) setState({ status: "error" });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}

function StatusMessage({ state }: { state: LoadState }) {
  if (state.status === "loading") {
    return <p className="mt-6 text-[13px] text-ink/62 dark:text-ink-dark/62">Loading…</p>;
  }
  if (state.status === "signed-out") {
    return (
      <p className="mt-6 text-[13px] leading-relaxed text-ink/65 dark:text-ink-dark/65">
        <Link href="/sign-in" className="underline decoration-ink/20 underline-offset-4 hover:decoration-ink/50">
          Sign in
        </Link>{" "}
        to see your balance and history.
      </p>
    );
  }
  if (state.status === "error") {
    return (
      <p className="mt-6 text-[13px] text-red-600/80 dark:text-red-400/80">
        Couldn&apos;t load your credits right now. Try refreshing.
      </p>
    );
  }
  return null;
}

/** The real balance + ledger history (server/credits.py), shared by
 * /dashboard/billing and /dashboard/usage - same data, different framing:
 * Billing leads with the balance and a buy-more link and shows every
 * transaction; Usage leads with recent spend and shows only debits
 * (reason === "adaptation"). Both are honest about `balance === null`
 * meaning "no database configured" (accounts don't exist at all on this
 * deployment), never rendering that as "0 credits" - see
 * server/credits.py::get_balance's own docstring for why those two
 * states must not be confused. */
export function CreditLedger({ view }: { view: "billing" | "usage" }) {
  const state = useCredits();

  if (state.status !== "ready") return <StatusMessage state={state} />;

  const { balance, transactions } = state.data;
  if (balance === null) {
    return (
      <p className="mt-6 text-[13px] leading-relaxed text-ink/65 dark:text-ink-dark/65">
        Accounts aren&apos;t configured on this deployment yet.
      </p>
    );
  }

  const rows = view === "usage" ? transactions.filter((t) => t.reason === "adaptation") : transactions;

  return (
    <div className="mt-6">
      <div className="rounded-2xl border border-black/[0.10] px-7 py-6 dark:border-white/[0.11]">
        <p className="text-[12px] uppercase tracking-[0.1em] text-ink/62 dark:text-ink-dark/62">
          Current balance
        </p>
        <p className="mt-2 font-serif text-3xl text-ink dark:text-ink-dark">
          {balance.toLocaleString()} <span className="text-[15px] font-sans text-ink/65 dark:text-ink-dark/65">credits</span>
        </p>
        {view === "billing" && (
          <Link
            href="/pricing"
            className="mt-4 inline-block rounded-full bg-ink px-5 py-2 text-[13px] font-medium text-paper transition active:scale-[0.97] dark:bg-ink-dark dark:text-paper-dark"
          >
            Buy more credits
          </Link>
        )}
      </div>

      <h2 className="mt-8 text-[13px] font-medium uppercase tracking-[0.08em] text-ink/62 dark:text-ink-dark/62">
        {view === "usage" ? "Recent usage" : "History"}
      </h2>
      {rows.length === 0 ? (
        <p className="mt-3 text-[13px] text-ink/62 dark:text-ink-dark/62">
          {view === "usage" ? "No adaptations run yet." : "No transactions yet."}
        </p>
      ) : (
        <ul className="mt-3 divide-y divide-black/[0.09] dark:divide-white/[0.09]">
          {rows.map((row) => (
            <li key={row.id} className="flex items-center justify-between py-3 text-[13px]">
              <div>
                <p className="text-ink/80 dark:text-ink-dark/80">{REASON_LABELS[row.reason]}</p>
                <p className="mt-0.5 text-[12px] text-ink/62 dark:text-ink-dark/62">
                  {formatDate(row.createdAt)}
                </p>
              </div>
              <p
                className={
                  row.amount > 0
                    ? "font-medium text-emerald-600 dark:text-emerald-400"
                    : "font-medium text-ink/78 dark:text-ink-dark/78"
                }
              >
                {row.amount > 0 ? "+" : ""}
                {row.amount.toLocaleString()}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

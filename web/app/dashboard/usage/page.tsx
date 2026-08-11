import { SiteHeader } from "@/components/SiteHeader";
import { DashboardSidebar } from "@/components/DashboardSidebar";
import { CreditLedger } from "@/components/CreditLedger";

export const metadata = { title: "CASTIA — Usage" };

// No longer a DashboardStub: signed-in usage is metered in real credits
// now (server/credits.py, charged per section/panel actually adapted -
// server/main.py's CREDITS_PER_SECTION/CREDITS_PER_PANEL), not just the
// anonymous per-IP quota (server/quota.py) that still gates requests
// with no account behind them. This is the debit side of the same
// ledger Billing shows in full.
export default function UsagePage() {
  return (
    <main className="min-h-screen px-6 pb-28 pt-8 sm:px-10">
      <div className="mx-auto max-w-5xl">
        <SiteHeader />

        <div className="mt-10 flex flex-col gap-10 sm:flex-row">
          <DashboardSidebar active="usage" />

          <div className="min-w-0 flex-1">
            <h1 className="font-serif text-2xl text-ink dark:text-ink-dark sm:text-[1.75rem]">
              Usage
            </h1>
            <p className="mt-2 max-w-prose text-[13px] leading-relaxed text-ink/62 dark:text-ink-dark/62">
              Your current balance and every adaptation charged against it,
              most recent first.
            </p>
            <CreditLedger view="usage" />
          </div>
        </div>
      </div>
    </main>
  );
}

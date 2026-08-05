import { SiteHeader } from "@/components/SiteHeader";
import { DashboardSidebar } from "@/components/DashboardSidebar";
import { CreditLedger } from "@/components/CreditLedger";

export const metadata = { title: "CASTIA — Billing" };

// No longer a DashboardStub: the credit ledger (server/credits.py) is
// real now - balance and full transaction history, plus a link to
// /pricing to buy more. Checkout itself (components/BuyButton.tsx) is
// wired to real Paddle.js, but still degrades to "not live yet" until a
// real Paddle account and price ids exist for this deployment.
export default function BillingPage() {
  return (
    <main className="min-h-screen px-6 pb-28 pt-8 sm:px-10">
      <div className="mx-auto max-w-5xl">
        <SiteHeader />

        <div className="mt-10 flex flex-col gap-10 sm:flex-row">
          <DashboardSidebar active="billing" />

          <div className="min-w-0 flex-1">
            <h1 className="font-serif text-2xl text-ink dark:text-ink-dark sm:text-[1.75rem]">
              Billing
            </h1>
            <p className="mt-2 max-w-prose text-[13px] leading-relaxed text-ink/40 dark:text-ink-dark/40">
              Your credit balance and every purchase, renewal, adaptation charge,
              and refund on it, most recent first.
            </p>
            <CreditLedger view="billing" />
          </div>
        </div>
      </div>
    </main>
  );
}

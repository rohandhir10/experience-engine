import { SiteHeader } from "@/components/SiteHeader";
import { Footer } from "@/components/Footer";

export const metadata = {
  title: "Refund & Cancellation Policy",
  description: "When credits are automatically restored, and how to request a refund on a purchase.",
  alternates: { canonical: "/refunds" },
};

// DRAFT, not legal advice - see terms/page.tsx's docstring for the same
// caveat. §1 describes real, already-implemented behavior
// (server/credits.py::refund, called automatically by server/main.py on
// ValidationError/LLMError/RuntimeError) - not aspirational copy. §2/§3
// describe the purchase-refund side, which depends on business decisions
// (refund window, exceptions) and the live payment processor's own
// policies, neither of which this repo can decide unilaterally.
export default function RefundsPage() {
  return (
    <main className="min-h-screen px-6 pb-28 pt-8 sm:px-10">
      <div className="mx-auto max-w-3xl">
        <SiteHeader />

        <div className="mt-10">
          <h1 className="font-serif text-3xl text-ink dark:text-ink-dark sm:text-4xl">
            Refund &amp; Cancellation Policy
          </h1>
          <p className="mt-3 text-[13px] text-ink/40 dark:text-ink-dark/40">
            Last updated: [DATE] · DRAFT — pending legal review, not yet in effect
          </p>
        </div>

        <div className="mt-10 space-y-9 text-[14px] leading-relaxed text-ink/70 dark:text-ink-dark/70">
          <Section title="1. Failed adaptations — automatic, no request needed">
            <p>
              If you're charged credits for an adaptation and it fails on
              Castia's side — an AI provider error, a validation problem, or
              an internal error — the credits are automatically returned to
              your balance as part of that same request. This happens
              server-side, immediately, and you don't need to contact
              support or file a request for it.
            </p>
            <p className="mt-3">
              This does not cover a result you're simply unhappy with: a
              completed adaptation that ran successfully but that you feel
              is a poor creative choice is not a "failure" in this sense —
              credits are charged for the AI run being performed, not for a
              specific quality outcome being guaranteed.
            </p>
          </Section>

          <Section title="2. Purchased credit packages">
            <p>
              Where paid credit purchases are live, purchases are processed
              by <Placeholder>Paddle (or the live payment processor at time of launch)</Placeholder>,
              acting as merchant of record for the transaction. Refund
              eligibility for a purchase is:
            </p>
            <ul className="mt-2 list-disc space-y-1.5 pl-5">
              <li>
                <Placeholder>
                  Eligibility window and conditions — e.g. "a full refund is
                  available within 14 days of purchase for credit packages
                  that remain substantially unused (fewer than X% of
                  purchased credits consumed)." This is a business decision
                  the product owner must set, consistent with the payment
                  processor's own merchant-of-record refund policy.
                </Placeholder>
              </li>
            </ul>
            <p className="mt-3">
              To request a refund on a purchase, contact{" "}
              <Placeholder>support@usecastia.com or your real support inbox</Placeholder>{" "}
              with your account email and the purchase date. Because{" "}
              <Placeholder>Paddle (or the live payment processor)</Placeholder>{" "}
              is the merchant of record, approved refunds are issued through
              their system to your original payment method, subject to their
              own processing timelines.
            </p>
          </Section>

          <Section title="3. Subscriptions">
            <p>
              <Placeholder>
                If/when a recurring subscription tier is introduced (as
                opposed to one-time credit packages), this section needs
                cancellation mechanics (self-service cancel, effective date
                — end of current period vs. immediate, and whether a partial
                refund is offered for the unused remainder). Not yet
                applicable to the current one-time-credit-purchase model.
              </Placeholder>
            </p>
          </Section>

          <Section title="4. Chargebacks">
            <p>
              If you dispute a charge directly with your bank or card issuer
              (a chargeback) instead of requesting a refund through us
              first, we reserve the right to suspend the associated
              account's access to the Service while the dispute is resolved.
              We'd rather resolve a billing problem directly — contact{" "}
              <Placeholder>support@usecastia.com or your real support inbox</Placeholder>{" "}
              first if something looks wrong on a charge.
            </p>
          </Section>
        </div>

        <Footer />
      </div>
    </main>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h2 className="font-serif text-lg text-ink dark:text-ink-dark">{title}</h2>
      <div className="mt-2.5">{children}</div>
    </div>
  );
}

function Placeholder({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded bg-amber-500/10 px-1.5 py-0.5 text-amber-700 dark:text-amber-400">
      [{children}]
    </span>
  );
}

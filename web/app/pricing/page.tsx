import { SiteHeader } from "@/components/SiteHeader";
import { Footer } from "@/components/Footer";

export const metadata = {
  title: "Pricing",
  description: "Plans for Castia. Billing isn't live yet — the Free tier is.",
  alternates: { canonical: "/pricing" },
};

const TIERS = [
  {
    name: "Free",
    blurb: "Try CASTIA with no account.",
    features: ["A few adaptations per day", "Full comparison view", "No credit card"],
  },
  {
    name: "Creator",
    blurb: "For songwriters and translators adapting regularly.",
    features: ["Higher monthly limit", "Adaptation history", "Priority processing"],
  },
  {
    name: "Studio",
    blurb: "For teams shipping adaptations at volume.",
    features: ["Team seats", "Bulk adaptation", "Early access to the API"],
  },
  {
    name: "Enterprise",
    blurb: "Custom volume, SLAs, and support.",
    features: ["Custom usage limits", "Dedicated support", "Contract & invoicing"],
  },
];

export default function PricingPage() {
  return (
    <main className="min-h-screen px-6 pb-28 pt-8 sm:px-10">
      <div className="mx-auto max-w-3xl">
        <SiteHeader active="pricing" />

        <div className="mt-10">
          <h1 className="font-serif text-3xl text-ink dark:text-ink-dark sm:text-4xl">
            Pricing.
          </h1>
          <p className="mt-4 max-w-prose text-[15px] leading-relaxed text-ink/55 dark:text-ink-dark/55">
            CASTIA is free to try right now, for everyone, with no account
            needed. These are the plans we're building toward — billing
            isn't live yet, so nothing below is charged.
          </p>
        </div>

        <div className="mt-12 grid gap-5 sm:grid-cols-2">
          {TIERS.map((tier) => (
            <div
              key={tier.name}
              className="rounded-2xl border border-black/[0.06] px-7 py-8 dark:border-white/[0.07]"
            >
              <p className="font-serif text-xl text-ink dark:text-ink-dark">
                {tier.name}
              </p>
              <p className="mt-2 text-[13px] leading-relaxed text-ink/45 dark:text-ink-dark/45">
                {tier.blurb}
              </p>
              <ul className="mt-5 space-y-2">
                {tier.features.map((f) => (
                  <li
                    key={f}
                    className="text-[13px] leading-relaxed text-ink/60 dark:text-ink-dark/60"
                  >
                    {f}
                  </li>
                ))}
              </ul>
              <p className="mt-6 text-[12px] uppercase tracking-[0.1em] text-ink/30 dark:text-ink-dark/30">
                Coming soon
              </p>
            </div>
          ))}
        </div>

        <Footer />
      </div>
    </main>
  );
}

import { SiteHeader } from "@/components/SiteHeader";
import { Footer } from "@/components/Footer";
import { BuyButton } from "@/components/BuyButton";
import { JsonLd } from "@/components/JsonLd";
import { BreadcrumbNav } from "@/components/BreadcrumbNav";
import Link from "next/link";
import { contentByPath } from "@/lib/content";
import { breadcrumbJsonLd, productJsonLd } from "@/lib/schema";

const entry = contentByPath("/pricing")!;

export const metadata = {
  title: entry.title,
  description: entry.description,
  alternates: { canonical: entry.path },
};

// One credit unit throughout this page. A typical five-panel comic or webtoon page is the pricing reference.
const PAGE_CREDITS = 50; // a typical 5-panel manga/webtoon page

type Pack = { name: string; price: number; credits: number; blurb: string; priceId?: string };

// Price IDs come from Paddle's own dashboard once a real product/price
// exists there (this project has no API credentials to create them,
// only to receive webhooks about them - server/paddle.py) - unset until
// then, which is why BuyButton degrades to "not live yet" rather than
// erroring when priceId is undefined.
const PACKS: Pack[] = [
  {
    name: "Starter",
    price: 10,
    credits: 144,
    blurb: "A one-time pack. No expiry, no commitment.",
    priceId: process.env.NEXT_PUBLIC_PADDLE_PRICE_STARTER,
  },
  {
    name: "Growth",
    price: 29,
    credits: 464,
    blurb: "The best per-credit rate of the one-time packs.",
    priceId: process.env.NEXT_PUBLIC_PADDLE_PRICE_GROWTH,
  },
  {
    name: "Bulk",
    price: 99,
    credits: 1584,
    blurb: "For a full project's worth of adaptations in one purchase.",
    priceId: process.env.NEXT_PUBLIC_PADDLE_PRICE_BULK,
  },
];

const SUBSCRIPTION = {
  name: "Creator",
  price: 17,
  credits: 272,
  blurb: "272 credits delivered every month, at the same rate as Bulk - so subscribing never costs more per credit than buying a pack outright.",
  priceId: process.env.NEXT_PUBLIC_PADDLE_PRICE_CREATOR,
};

function perPage(price: number, credits: number): string {
  return ((price / credits) * PAGE_CREDITS).toFixed(2);
}

// Original artwork, not a screenshot - states the one fact that actually
// makes this pricing page unusual: everything below is free today, not a
// discount or a trial, because billing simply isn't wired up yet. Real
// and disclosed elsewhere in this page's prose; this just makes it
// visible at a glance instead of hero copy alone carrying it.
function FreeRightNowPanel() {
  return (
    <div className="rounded-2xl border border-black/[0.12] bg-paper p-6 dark:border-white/[0.12] dark:bg-paper-dark sm:p-7">
      <p className="text-[10px] font-medium uppercase tracking-[0.1em] text-accent">
        Right now
      </p>
      <p className="mt-2 font-serif text-2xl text-ink dark:text-ink-dark">Free</p>
      <p className="mt-1.5 text-[13px] leading-relaxed text-ink/78 dark:text-ink-dark/78">
        No account, no card, no limit tier - billing isn't live.
      </p>

      <div className="my-5 border-t border-dashed border-black/10 dark:border-white/10" />

      <p className="text-[10px] font-medium uppercase tracking-[0.1em] text-ink/75 dark:text-ink-dark/75">
        Building toward
      </p>
      <p className="mt-2 font-serif text-2xl text-ink/62 dark:text-ink-dark/62">
        ${PACKS[0].price}&ndash;${SUBSCRIPTION.price}
        <span className="text-[13px] font-sans text-ink/75 dark:text-ink-dark/75"> credits &amp; monthly</span>
      </p>
      <p className="mt-1.5 text-[13px] leading-relaxed text-ink/68 dark:text-ink-dark/68">
        The tiers below, once Paddle checkout goes live.
      </p>
    </div>
  );
}

export default function PricingPage() {
  const breadcrumb = breadcrumbJsonLd([
    { name: "Home", path: "/" },
    { name: "Pricing" },
  ]);
  // availability: PreOrder, not InStock - matches the page's own visible
  // disclosure that Paddle checkout isn't live yet. Structured data has
  // to agree with what a visitor actually sees, same rule the FAQ page's
  // JSON-LD follows.
  const product = productJsonLd({
    path: entry.path,
    name: "Castia credits",
    description: entry.description,
    offers: [
      { name: "Starter", price: String(PACKS[0].price), priceCurrency: "USD", description: `${PACKS[0].credits} credits, one-time, no expiry` },
      { name: "Growth", price: String(PACKS[1].price), priceCurrency: "USD", description: `${PACKS[1].credits} credits, one-time, no expiry` },
      { name: "Bulk", price: String(PACKS[2].price), priceCurrency: "USD", description: `${PACKS[2].credits} credits, one-time, no expiry` },
      { name: SUBSCRIPTION.name, price: String(SUBSCRIPTION.price), priceCurrency: "USD", description: `${SUBSCRIPTION.credits} credits delivered monthly` },
    ],
    availability: "https://schema.org/PreOrder",
  });

  return (
    <main className="castia-interior min-h-screen px-5 pb-24 pt-6 sm:px-8 sm:pt-8">
      <JsonLd data={breadcrumb} />
      <JsonLd data={product} />
      <div className="mx-auto max-w-5xl">
        <SiteHeader active="pricing" />

        <div className="castia-pricing-hero mt-10 grid grid-cols-1 gap-10 lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
          <div>
            <BreadcrumbNav items={[{ name: "Home", path: "/" }, { name: "Pricing" }]} />
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-accent">Simple, transparent economics</p>
            <h1 className="mt-3 font-serif text-4xl text-ink dark:text-ink-dark sm:text-5xl">
              Pricing that scales with your story.
            </h1>
            {/* Short, not the old two-sentence hedge/caveat - the panel
                beside it (FreeRightNowPanel) already states the same
                facts (free right now, no account, the pricing below is
                what's coming) visually, so the paragraph doesn't need to
                re-explain them in prose too. Real feedback that the site
                read as text-heavy; the fuller disclosure still exists in
                this page's own meta description (entry.description
                above), untouched. */}
            <p className="mt-4 max-w-prose text-[15px] leading-relaxed text-ink/78 dark:text-ink-dark/78">
              Free to use right now, for everyone. What's below is the
              pricing we're building toward, not what you pay today.
            </p>
          </div>
          <FreeRightNowPanel />
        </div>

        <section className="castia-credit-explainer mt-16 rounded-3xl border border-black/[0.09] bg-white/45 p-6 dark:border-white/[0.11] dark:bg-white/[0.025] sm:p-8">
          <div className="grid gap-8 lg:grid-cols-[0.8fr_1.2fr] lg:items-start">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-accent">Understand the unit</p>
              <h2 className="mt-2 font-serif text-2xl text-ink dark:text-ink-dark">How credits work</h2>
              <p className="mt-3 text-[14px] leading-relaxed text-ink/78 dark:text-ink-dark/78">
                One credit is one unit of adaptation work. The page estimate is a practical starting point, not a fixed quote.
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-2xl border border-black/[0.08] bg-paper/75 p-4 dark:border-white/[0.1] dark:bg-white/[0.035]">
                <p className="text-[10px] font-medium uppercase tracking-[0.12em] text-ink/60 dark:text-ink-dark/60">01 / Unit</p>
                <p className="mt-2 font-serif text-xl text-ink dark:text-ink-dark">1 credit</p>
                <p className="mt-1 text-[12px] leading-relaxed text-ink/70 dark:text-ink-dark/70">One unit of adaptation work.</p>
              </div>
              <div className="rounded-2xl border border-black/[0.08] bg-paper/75 p-4 dark:border-white/[0.1] dark:bg-white/[0.035]">
                <p className="text-[10px] font-medium uppercase tracking-[0.12em] text-ink/60 dark:text-ink-dark/60">02 / Typical page</p>
                <p className="mt-2 font-serif text-xl text-ink dark:text-ink-dark">{PAGE_CREDITS} credits</p>
                <p className="mt-1 text-[12px] leading-relaxed text-ink/70 dark:text-ink-dark/70">Around five panels, including OCR and optional redraw.</p>
              </div>
              <div className="rounded-2xl border border-black/[0.08] bg-paper/75 p-4 dark:border-white/[0.1] dark:bg-white/[0.035]">
                <p className="text-[10px] font-medium uppercase tracking-[0.12em] text-ink/60 dark:text-ink-dark/60">03 / Actual usage</p>
                <p className="mt-2 font-serif text-xl text-ink dark:text-ink-dark">Variable</p>
                <p className="mt-1 text-[12px] leading-relaxed text-ink/70 dark:text-ink-dark/70">Dense pages can cost more; sparse pages can cost less.</p>
              </div>
            </div>
          </div>
          <p className="mt-6 border-t border-black/[0.08] pt-4 text-[13px] leading-relaxed text-ink/70 dark:border-white/[0.1] dark:text-ink-dark/70">
            For comparison, professional manga localization freelancers may charge $5/page and up for translation alone, before typesetting. At Starter-pack rates, a full page here — translated, redrawn, and typeset — is estimated below that floor.
          </p>
        </section>

        <section className="castia-price-section mt-16">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-accent">One-time purchase</p>
              <h2 className="mt-2 font-serif text-2xl text-ink dark:text-ink-dark">Pay-as-you-go credit packs</h2>
            </div>
            <p className="max-w-sm text-[13px] leading-relaxed text-ink/70 dark:text-ink-dark/70">Buy once, use whenever. Pack credits don’t expire.</p>
          </div>
          <p className="mt-3 max-w-prose text-[14px] leading-relaxed text-ink/78 dark:text-ink-dark/78">
            Buy credits once, use them whenever. They don't expire and
            they're never charged again on their own.
          </p>
          <div className="mt-6 grid gap-5 sm:grid-cols-3">
            {PACKS.map((pack) => (
              <div
                key={pack.name}
                className={`castia-price-card rounded-2xl border px-6 py-7 dark:border-white/[0.11] ${pack.name === "Growth" ? "castia-price-card-featured border-accent/50 bg-accent/[0.055]" : "border-black/[0.10]"}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <p className="font-serif text-xl text-ink dark:text-ink-dark">{pack.name}</p>
                  {pack.name === "Growth" ? <span className="rounded-full border border-accent/35 px-2.5 py-1 text-[9px] font-semibold uppercase tracking-[0.1em] text-accent">Best rate</span> : null}
                </div>
                <p className="mt-2 text-2xl text-ink dark:text-ink-dark">
                  ${pack.price}
                </p>
                <p className="mt-1 text-[13px] text-ink/75 dark:text-ink-dark/75">
                  {pack.credits.toLocaleString()} credits
                </p>
                <p className="mt-4 text-[13px] leading-relaxed text-ink/72 dark:text-ink-dark/72">
                  {pack.blurb}
                </p>
                <p className="mt-4 text-[12px] leading-relaxed text-ink/62 dark:text-ink-dark/62">
                  ~${perPage(pack.price, pack.credits)}/page
                </p>
                <div className="mt-6">
                  <BuyButton priceId={pack.priceId} label={`Buy ${pack.name}`} />
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="castia-price-section mt-16 border-t border-black/[0.09] pt-10 dark:border-white/[0.11]">
          <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-accent">For regular releases</p>
          <h2 className="mt-2 font-serif text-2xl text-ink dark:text-ink-dark">Creator subscription</h2>
          <p className="mt-3 max-w-prose text-[14px] leading-relaxed text-ink/78 dark:text-ink-dark/78">
            For regular use without buying a new pack every time.
          </p>
          <div className="castia-price-card mt-6 rounded-2xl border border-black/[0.10] bg-white/45 px-7 py-8 dark:border-white/[0.11] dark:bg-white/[0.025] sm:max-w-lg">
            <p className="font-serif text-xl text-ink dark:text-ink-dark">
              {SUBSCRIPTION.name}
            </p>
            <p className="mt-2 text-2xl text-ink dark:text-ink-dark">
              ${SUBSCRIPTION.price}
              <span className="text-[14px] text-ink/75 dark:text-ink-dark/75">
                {" "}
                / month
              </span>
            </p>
            <p className="mt-1 text-[13px] text-ink/75 dark:text-ink-dark/75">
              {SUBSCRIPTION.credits.toLocaleString()} credits / month
            </p>
            <p className="mt-4 text-[13px] leading-relaxed text-ink/72 dark:text-ink-dark/72">
              {SUBSCRIPTION.blurb}
            </p>
            <p className="mt-4 text-[12px] leading-relaxed text-ink/62 dark:text-ink-dark/62">
              ~${perPage(SUBSCRIPTION.price, SUBSCRIPTION.credits)}/page
            </p>
            <div className="mt-6">
              <BuyButton priceId={SUBSCRIPTION.priceId} label="Subscribe" />
            </div>
          </div>
        </section>

        <section className="castia-price-section mt-16 border-t border-black/[0.09] pt-10 dark:border-white/[0.11]">
          <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-ink/60 dark:text-ink-dark/60">On the roadmap</p>
          <h2 className="mt-2 font-serif text-2xl text-ink dark:text-ink-dark">Studio &amp; Enterprise</h2>
          {/* Dashed border, not the same solid-border card the live tiers
              above use - matching that treatment made "Coming soon" easy
              to miss at a glance (real feedback: these read as
              purchasable at the same weight as Starter/Growth/Bulk/
              Creator). Same "not live yet" visual language as
              PanelUploader's dropzone and DashboardSidebar's "Soon" rows
              use elsewhere. Dimmed via each text element's own opacity,
              NOT a container-level `opacity-*` wrapping the card - that
              would multiply against every child's own opacity (a
              text-ink/70 inside an opacity-60 container renders at an
              effective ~33%, not 55%), which is real, caught only by
              actually recomputing rendered contrast rather than trusting
              the source class name. "Coming soon" - the one thing on
              this card a visitor actually needs to read - stays at full
              AA contrast; only the decorative framing dims. */}
          <div className="mt-6 grid gap-5 sm:grid-cols-2">
            <div className="rounded-2xl border border-dashed border-black/[0.15] px-7 py-8 dark:border-white/20">
              <p className="font-serif text-xl text-ink/78 dark:text-ink-dark/78">
                Studio
              </p>
              <p className="mt-2 text-[13px] leading-relaxed text-ink/62 dark:text-ink-dark/62">
                For teams shipping adaptations at volume.
              </p>
              <ul className="mt-5 space-y-2">
                {["Team seats", "Pooled credits", "Bulk credit discount", "Early access to the API"].map(
                  (f) => (
                    <li
                      key={f}
                      className="text-[13px] leading-relaxed text-ink/75 dark:text-ink-dark/75"
                    >
                      {f}
                    </li>
                  )
                )}
              </ul>
              <p className="mt-6 text-[12px] font-medium uppercase tracking-[0.1em] text-ink/78 dark:text-ink-dark/78">
                Coming soon
              </p>
            </div>
            <div className="rounded-2xl border border-dashed border-black/[0.15] px-7 py-8 dark:border-white/20">
              <p className="font-serif text-xl text-ink/78 dark:text-ink-dark/78">
                Enterprise
              </p>
              <p className="mt-2 text-[13px] leading-relaxed text-ink/62 dark:text-ink-dark/62">
                Custom volume, SLAs, and support.
              </p>
              <ul className="mt-5 space-y-2">
                {["Custom credit volume", "Dedicated support", "Contract & invoicing"].map(
                  (f) => (
                    <li
                      key={f}
                      className="text-[13px] leading-relaxed text-ink/75 dark:text-ink-dark/75"
                    >
                      {f}
                    </li>
                  )
                )}
              </ul>
              <p className="mt-6 text-[12px] font-medium uppercase tracking-[0.1em] text-ink/78 dark:text-ink-dark/78">
                Coming soon
              </p>
            </div>
          </div>
        </section>

        <section className="castia-price-section mt-16 border-t border-black/[0.09] pt-10 dark:border-white/[0.11]">
          <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-accent">Good to know</p>
          <h2 className="mt-2 font-serif text-2xl text-ink dark:text-ink-dark">Credits, in detail</h2>
          <div className="mt-6 space-y-6">
            <div>
              <h3 className="text-[14px] font-medium text-ink dark:text-ink-dark">
                What happens if a generation fails?
              </h3>
              <p className="mt-1.5 max-w-prose text-[13.5px] leading-relaxed text-ink/78 dark:text-ink-dark/78">
                Credits are debited when a job starts, before the engine
                runs, so a job can't begin without its cost already locked
                in. If the underlying model or inpainting call fails after
                that debit, the credits are refunded automatically — you're
                never charged for a run that didn't produce a result.
              </p>
            </div>
            <div>
              <h3 className="text-[14px] font-medium text-ink dark:text-ink-dark">
                Do credits expire?
              </h3>
              <p className="mt-1.5 max-w-prose text-[13.5px] leading-relaxed text-ink/78 dark:text-ink-dark/78">
                Pay-as-you-go pack credits don't expire and aren't charged
                again on their own. Creator subscription credits are
                delivered to the same balance every month for as long as
                the subscription is active.
              </p>
            </div>
            <div>
              <h3 className="text-[14px] font-medium text-ink dark:text-ink-dark">
                Refunds, once billing is live
              </h3>
              <p className="mt-1.5 max-w-prose text-[13.5px] leading-relaxed text-ink/78 dark:text-ink-dark/78">
                Failed generations are refunded automatically, as above.
                For everything else — the general refund policy once
                purchases are actually live — see the{" "}
                <Link href="/refunds" className="underline decoration-ink/20 underline-offset-4">
                  refund policy
                </Link>
                .
              </p>
            </div>
          </div>
        </section>

        <Footer />
      </div>
    </main>
  );
}

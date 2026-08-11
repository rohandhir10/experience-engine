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

// One credit unit throughout this page. Keeping these three numbers in
// one place means the $/song and $/page figures below are derived, not
// separately hand-typed - the two can't drift out of sync with each
// other the way two independently-written numbers could.
const SONG_CREDITS = 30; // a typical ~6-section song adaptation
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

function perSong(price: number, credits: number): string {
  return ((price / credits) * SONG_CREDITS).toFixed(2);
}

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
      <p className="text-[10px] font-medium uppercase tracking-[0.1em] text-accent/70">
        Right now
      </p>
      <p className="mt-2 font-serif text-2xl text-ink dark:text-ink-dark">Free</p>
      <p className="mt-1.5 text-[13px] leading-relaxed text-ink/55 dark:text-ink-dark/55">
        No account, no card, no limit tier - billing isn't live.
      </p>

      <div className="my-5 border-t border-dashed border-black/10 dark:border-white/10" />

      <p className="text-[10px] font-medium uppercase tracking-[0.1em] text-ink/35 dark:text-ink-dark/35">
        Building toward
      </p>
      <p className="mt-2 font-serif text-2xl text-ink/40 dark:text-ink-dark/40">
        ${PACKS[0].price}&ndash;${SUBSCRIPTION.price}
        <span className="text-[13px] font-sans text-ink/35 dark:text-ink-dark/35"> credits &amp; monthly</span>
      </p>
      <p className="mt-1.5 text-[13px] leading-relaxed text-ink/50 dark:text-ink-dark/50">
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
    <main className="min-h-screen px-6 pb-28 pt-8 sm:px-10">
      <JsonLd data={breadcrumb} />
      <JsonLd data={product} />
      <div className="mx-auto max-w-3xl">
        <SiteHeader active="pricing" />

        <div className="mt-10 grid grid-cols-1 gap-10 lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
          <div>
            <BreadcrumbNav items={[{ name: "Home", path: "/" }, { name: "Pricing" }]} />
            <h1 className="mt-3 font-serif text-3xl text-ink dark:text-ink-dark sm:text-4xl">
              Pricing.
            </h1>
            <p className="mt-4 max-w-prose text-[15px] leading-relaxed text-ink/55 dark:text-ink-dark/55">
              CASTIA is free to try right now, for everyone, with no
              account needed - that's a limitation of billing not existing
              yet, not the plan. What's below is the credit-based pricing
              we're building toward, and every tier in it is paid: checkout
              will run through Paddle, but until it's live, nothing here is
              charged today.
            </p>
          </div>
          <FreeRightNowPanel />
        </div>

        <section className="mt-12">
          <h2 className="font-serif text-xl text-ink dark:text-ink-dark">
            How credits work
          </h2>
          <p className="mt-3 max-w-prose text-[14px] leading-relaxed text-ink/55 dark:text-ink-dark/55">
            One credit is one unit of adaptation work. A typical song
            (~6 sections) runs about {SONG_CREDITS} credits. A typical
            manga/webtoon page (~5 panels, including the OCR and redraw
            pass) runs about {PAGE_CREDITS} credits - typically around
            $3.50/page at Starter-pack rates, though a very dense page or
            one that needs the hosted redraw service can run higher, and a
            sparse one can run lower. Music and comics draw from the same
            credit balance.
          </p>
          <p className="mt-3 max-w-prose text-[14px] leading-relaxed text-ink/55 dark:text-ink-dark/55">
            For comparison: professional manga localization freelancers
            typically charge $5/page and up just for translation, before
            typesetting. At Starter-pack rates, a full page here - translated,
            redrawn, and typeset - costs less than that floor.
          </p>
        </section>

        <section className="mt-12">
          <h2 className="font-serif text-xl text-ink dark:text-ink-dark">
            Pay-as-you-go credit packs
          </h2>
          <p className="mt-3 max-w-prose text-[14px] leading-relaxed text-ink/55 dark:text-ink-dark/55">
            Buy credits once, use them whenever. They don't expire and
            they're never charged again on their own.
          </p>
          <div className="mt-6 grid gap-5 sm:grid-cols-3">
            {PACKS.map((pack) => (
              <div
                key={pack.name}
                className="rounded-2xl border border-black/[0.10] px-6 py-7 dark:border-white/[0.11]"
              >
                <p className="font-serif text-xl text-ink dark:text-ink-dark">
                  {pack.name}
                </p>
                <p className="mt-2 text-2xl text-ink dark:text-ink-dark">
                  ${pack.price}
                </p>
                <p className="mt-1 text-[13px] text-ink/45 dark:text-ink-dark/45">
                  {pack.credits.toLocaleString()} credits
                </p>
                <p className="mt-4 text-[13px] leading-relaxed text-ink/60 dark:text-ink-dark/60">
                  {pack.blurb}
                </p>
                <p className="mt-4 text-[12px] leading-relaxed text-ink/40 dark:text-ink-dark/40">
                  ~${perSong(pack.price, pack.credits)}/song · ~$
                  {perPage(pack.price, pack.credits)}/page
                </p>
                <div className="mt-6">
                  <BuyButton priceId={pack.priceId} label={`Buy ${pack.name}`} />
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="mt-12">
          <h2 className="font-serif text-xl text-ink dark:text-ink-dark">
            Creator subscription
          </h2>
          <p className="mt-3 max-w-prose text-[14px] leading-relaxed text-ink/55 dark:text-ink-dark/55">
            For regular use without buying a new pack every time.
          </p>
          <div className="mt-6 rounded-2xl border border-black/[0.10] px-7 py-8 dark:border-white/[0.11] sm:max-w-sm">
            <p className="font-serif text-xl text-ink dark:text-ink-dark">
              {SUBSCRIPTION.name}
            </p>
            <p className="mt-2 text-2xl text-ink dark:text-ink-dark">
              ${SUBSCRIPTION.price}
              <span className="text-[14px] text-ink/45 dark:text-ink-dark/45">
                {" "}
                / month
              </span>
            </p>
            <p className="mt-1 text-[13px] text-ink/45 dark:text-ink-dark/45">
              {SUBSCRIPTION.credits.toLocaleString()} credits / month
            </p>
            <p className="mt-4 text-[13px] leading-relaxed text-ink/60 dark:text-ink-dark/60">
              {SUBSCRIPTION.blurb}
            </p>
            <p className="mt-4 text-[12px] leading-relaxed text-ink/40 dark:text-ink-dark/40">
              ~${perSong(SUBSCRIPTION.price, SUBSCRIPTION.credits)}/song · ~$
              {perPage(SUBSCRIPTION.price, SUBSCRIPTION.credits)}/page
            </p>
            <div className="mt-6">
              <BuyButton priceId={SUBSCRIPTION.priceId} label="Subscribe" />
            </div>
          </div>
        </section>

        <section className="mt-12">
          <h2 className="font-serif text-xl text-ink dark:text-ink-dark">
            Studio &amp; Enterprise
          </h2>
          <div className="mt-6 grid gap-5 sm:grid-cols-2">
            <div className="rounded-2xl border border-black/[0.10] px-7 py-8 dark:border-white/[0.11]">
              <p className="font-serif text-xl text-ink dark:text-ink-dark">
                Studio
              </p>
              <p className="mt-2 text-[13px] leading-relaxed text-ink/45 dark:text-ink-dark/45">
                For teams shipping adaptations at volume.
              </p>
              <ul className="mt-5 space-y-2">
                {["Team seats", "Pooled credits", "Bulk credit discount", "Early access to the API"].map(
                  (f) => (
                    <li
                      key={f}
                      className="text-[13px] leading-relaxed text-ink/60 dark:text-ink-dark/60"
                    >
                      {f}
                    </li>
                  )
                )}
              </ul>
              <p className="mt-6 text-[12px] uppercase tracking-[0.1em] text-ink/30 dark:text-ink-dark/30">
                Coming soon
              </p>
            </div>
            <div className="rounded-2xl border border-black/[0.10] px-7 py-8 dark:border-white/[0.11]">
              <p className="font-serif text-xl text-ink dark:text-ink-dark">
                Enterprise
              </p>
              <p className="mt-2 text-[13px] leading-relaxed text-ink/45 dark:text-ink-dark/45">
                Custom volume, SLAs, and support.
              </p>
              <ul className="mt-5 space-y-2">
                {["Custom credit volume", "Dedicated support", "Contract & invoicing"].map(
                  (f) => (
                    <li
                      key={f}
                      className="text-[13px] leading-relaxed text-ink/60 dark:text-ink-dark/60"
                    >
                      {f}
                    </li>
                  )
                )}
              </ul>
              <p className="mt-6 text-[12px] uppercase tracking-[0.1em] text-ink/30 dark:text-ink-dark/30">
                Coming soon
              </p>
            </div>
          </div>
        </section>

        <section className="mt-12 border-t border-black/[0.10] pt-10 dark:border-white/[0.11]">
          <h2 className="font-serif text-xl text-ink dark:text-ink-dark">
            Credits, in detail
          </h2>
          <div className="mt-6 space-y-6">
            <div>
              <h3 className="text-[14px] font-medium text-ink dark:text-ink-dark">
                What happens if a generation fails?
              </h3>
              <p className="mt-1.5 max-w-prose text-[13.5px] leading-relaxed text-ink/55 dark:text-ink-dark/55">
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
              <p className="mt-1.5 max-w-prose text-[13.5px] leading-relaxed text-ink/55 dark:text-ink-dark/55">
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
              <p className="mt-1.5 max-w-prose text-[13.5px] leading-relaxed text-ink/55 dark:text-ink-dark/55">
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

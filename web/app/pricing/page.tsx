import { SiteHeader } from "@/components/SiteHeader";
import { Footer } from "@/components/Footer";

export const metadata = {
  title: "Pricing",
  description:
    "Credit-based pricing for Castia. Billing isn't live yet - the Free tier is.",
  alternates: { canonical: "/pricing" },
};

// One credit unit throughout this page. Keeping these three numbers in
// one place means the $/song and $/page figures below are derived, not
// separately hand-typed - the two can't drift out of sync with each
// other the way two independently-written numbers could.
const SONG_CREDITS = 30; // a typical ~6-section song adaptation
const PAGE_CREDITS = 50; // a typical 5-panel manga/webtoon page

type Pack = { name: string; price: number; credits: number; blurb: string };

const PACKS: Pack[] = [
  {
    name: "Starter",
    price: 10,
    credits: 144,
    blurb: "A one-time pack. No expiry, no commitment.",
  },
  {
    name: "Growth",
    price: 29,
    credits: 464,
    blurb: "The best per-credit rate of the one-time packs.",
  },
  {
    name: "Bulk",
    price: 99,
    credits: 1584,
    blurb: "For a full project's worth of adaptations in one purchase.",
  },
];

const SUBSCRIPTION = {
  name: "Creator",
  price: 17,
  credits: 272,
  blurb: "272 credits delivered every month, at the same rate as Bulk - so subscribing never costs more per credit than buying a pack outright.",
};

function perSong(price: number, credits: number): string {
  return ((price / credits) * SONG_CREDITS).toFixed(2);
}

function perPage(price: number, credits: number): string {
  return ((price / credits) * PAGE_CREDITS).toFixed(2);
}

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
            needed. What's below is the credit-based pricing we're building
            toward - checkout will run through Paddle, but it isn't live
            yet, so nothing here is charged today.
          </p>
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
            Free
          </h2>
          <div className="mt-4 rounded-2xl border border-black/[0.06] px-7 py-8 dark:border-white/[0.07]">
            <p className="font-serif text-xl text-ink dark:text-ink-dark">
              A few adaptations every month
            </p>
            <p className="mt-2 max-w-prose text-[13px] leading-relaxed text-ink/45 dark:text-ink-dark/45">
              No account needed, no card. Enough to genuinely try Castia on a
              real song or comic page - not sized for daily or bulk use, since
              this tier isn't billed for.
            </p>
          </div>
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
                className="rounded-2xl border border-black/[0.06] px-6 py-7 dark:border-white/[0.07]"
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
                <p className="mt-6 text-[12px] uppercase tracking-[0.1em] text-ink/30 dark:text-ink-dark/30">
                  Coming soon
                </p>
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
          <div className="mt-6 rounded-2xl border border-black/[0.06] px-7 py-8 dark:border-white/[0.07] sm:max-w-sm">
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
            <p className="mt-6 text-[12px] uppercase tracking-[0.1em] text-ink/30 dark:text-ink-dark/30">
              Coming soon
            </p>
          </div>
        </section>

        <section className="mt-12">
          <h2 className="font-serif text-xl text-ink dark:text-ink-dark">
            Studio &amp; Enterprise
          </h2>
          <div className="mt-6 grid gap-5 sm:grid-cols-2">
            <div className="rounded-2xl border border-black/[0.06] px-7 py-8 dark:border-white/[0.07]">
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
            <div className="rounded-2xl border border-black/[0.06] px-7 py-8 dark:border-white/[0.07]">
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

        <Footer />
      </div>
    </main>
  );
}

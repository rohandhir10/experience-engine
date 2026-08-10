import { SiteHeader } from "@/components/SiteHeader";
import { Footer } from "@/components/Footer";
import { JsonLd } from "@/components/JsonLd";
import { BreadcrumbNav } from "@/components/BreadcrumbNav";
import Link from "next/link";
import { SITE_NAME, FOUNDER_NAME, absoluteUrl } from "@/lib/seo";
import { breadcrumbJsonLd } from "@/lib/schema";

export const metadata = {
  title: "About",
  description: `${SITE_NAME} is built and run by ${FOUNDER_NAME}.`,
  alternates: { canonical: "/about" },
};

// Kept deliberately minimal and factual - no invented founding story or
// credentials. What's here is what's actually true: who runs this,
// what the product is, what stage it's at, and how the editorial content
// elsewhere on the site sources its claims. See lib/seo.ts's FOUNDER_NAME
// comment for why this is the one page that gets a real Person bio.
const personJsonLd = {
  "@context": "https://schema.org",
  "@type": "Person",
  name: FOUNDER_NAME,
  url: absoluteUrl("/about"),
  jobTitle: "Founder",
  worksFor: { "@type": "Organization", name: SITE_NAME, url: absoluteUrl("/") },
};

export default function AboutPage() {
  const breadcrumb = breadcrumbJsonLd([{ name: "Home", path: "/" }, { name: "About" }]);

  return (
    <main className="min-h-screen px-6 pb-28 pt-8 sm:px-10">
      <JsonLd data={breadcrumb} />
      <JsonLd data={personJsonLd} />
      <div className="mx-auto max-w-3xl">
        <SiteHeader />

        <div className="mt-10">
          <BreadcrumbNav items={[{ name: "Home", path: "/" }, { name: "About" }]} />
          <h1 className="mt-3 font-serif text-3xl text-ink dark:text-ink-dark sm:text-4xl">
            About Castia
          </h1>
          <p className="mt-4 max-w-prose text-[15px] leading-relaxed text-ink/55 dark:text-ink-dark/55">
            Castia is built and run by {FOUNDER_NAME}.
          </p>
        </div>

        <section className="mt-12">
          <h2 className="font-serif text-xl text-ink dark:text-ink-dark">What Castia is</h2>
          <p className="mt-3 max-w-prose text-[14px] leading-relaxed text-ink/60 dark:text-ink-dark/60">
            Castia adapts song lyrics and comic/webtoon dialogue across six
            languages through a three-stage pipeline - a literal Translator
            anchor, five Creative Adapter rewrites, and a Judge that picks a
            winner and states its reason - instead of a single translation
            pass. The full mechanism is on{" "}
            <Link href="/how-it-works" className="underline decoration-ink/20 underline-offset-4">
              how it works
            </Link>
            . The comics side is in Beta; the specific rough edges are
            disclosed on the{" "}
            <Link href="/manga-webtoon-translation" className="underline decoration-ink/20 underline-offset-4">
              manga &amp; webtoon translation
            </Link>{" "}
            page rather than smoothed over.
          </p>
        </section>

        <section className="mt-12">
          <h2 className="font-serif text-xl text-ink dark:text-ink-dark">
            How the writing on this site is sourced
          </h2>
          <p className="mt-3 max-w-prose text-[14px] leading-relaxed text-ink/60 dark:text-ink-dark/60">
            Every outside claim in Castia's blog, comparison, and guide
            pages - a research finding, an industry rate, a competitor's own
            description of its technology - links to the actual source
            it's drawn from, listed openly at the bottom of that page. If a
            comparison page states what another tool does, it's citing that
            tool's own published description, not a guess.
          </p>
        </section>

        <p className="mt-12 max-w-prose text-[13px] leading-relaxed text-ink/45 dark:text-ink-dark/45">
          Questions about the product? Start with the{" "}
          <Link href="/faq" className="underline decoration-ink/20 underline-offset-4">
            FAQ
          </Link>{" "}
          or the{" "}
          <Link href="/docs/api" className="underline decoration-ink/20 underline-offset-4">
            API docs
          </Link>
          .
        </p>

        <Footer />
      </div>
    </main>
  );
}

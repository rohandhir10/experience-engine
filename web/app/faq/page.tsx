import { SiteHeader } from "@/components/SiteHeader";
import { Footer } from "@/components/Footer";
import { JsonLd } from "@/components/JsonLd";
import { BreadcrumbNav } from "@/components/BreadcrumbNav";
import Link from "next/link";
import { breadcrumbJsonLd, faqPageJsonLd } from "@/lib/schema";
import { FAQS, FAQ_CATEGORIES as CATEGORIES } from "@/lib/faqs";

export const metadata = {
  title: "FAQ",
  description:
    "Answers about comic and webtoon localization, supported languages, pricing, the API, and how CASTIA differs from literal translation.",
  alternates: { canonical: "/faq" },
};

export default function FaqPage() {
  const breadcrumb = breadcrumbJsonLd([{ name: "Home", path: "/" }, { name: "FAQ" }]);
  const faqJsonLd = faqPageJsonLd(FAQS);

  return (
    <main className="castia-interior min-h-screen px-5 pb-24 pt-6 sm:px-8 sm:pt-8">
      <JsonLd data={breadcrumb} />
      <JsonLd data={faqJsonLd} />
      <div className="mx-auto max-w-5xl">
        <SiteHeader />

        <div className="mt-10">
          <BreadcrumbNav items={[{ name: "Home", path: "/" }, { name: "FAQ" }]} />
          <h1 className="mt-3 font-serif text-3xl text-ink dark:text-ink-dark sm:text-4xl">
            Frequently asked questions.
          </h1>
          <p className="mt-4 max-w-prose text-[15px] leading-relaxed text-ink/78 dark:text-ink-dark/78">
            For the full pipeline explanation, see{" "}
            <Link href="/how-it-works" className="underline decoration-ink/20 underline-offset-4">
              how it works
            </Link>
            .
          </p>
        </div>

        <div className="mt-12 space-y-12">
          {CATEGORIES.map((category) => (
            <section key={category}>
              <h2 className="text-[11px] font-medium uppercase tracking-[0.1em] text-accent">
                {category}
              </h2>
              <div className="mt-4 space-y-7">
                {FAQS.filter((faq) => faq.category === category).map((faq) => (
                  <div key={faq.question} className="border-b border-black/[0.10] pb-7 dark:border-white/[0.11]">
                    <h3 className="font-serif text-lg text-ink dark:text-ink-dark">
                      {faq.question}
                    </h3>
                    <p className="mt-2.5 max-w-prose text-[14px] leading-relaxed text-ink/72 dark:text-ink-dark/72">
                      {faq.answer}
                    </p>
                  </div>
                ))}
              </div>
            </section>
          ))}
        </div>

        <Footer />
      </div>
    </main>
  );
}

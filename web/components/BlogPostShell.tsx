import type { ReactNode } from "react";
import Link from "next/link";
import { SiteHeader } from "@/components/SiteHeader";
import { Footer } from "@/components/Footer";
import { JsonLd } from "@/components/JsonLd";
import { BreadcrumbNav } from "@/components/BreadcrumbNav";
import { SourceList } from "@/components/SourceList";
import type { ContentEntry } from "@/lib/content";
import { breadcrumbJsonLd, articleJsonLd, type Citation } from "@/lib/schema";
import { FOUNDER_NAME } from "@/lib/seo";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" });
}

/** Shared scaffolding for every /blog/[slug] post - breadcrumb + Article
 * JSON-LD (dates and citations sourced from lib/content.ts / the page's
 * own SOURCES so structured data and visible content can't drift apart),
 * a real "Published/Updated" line, the post body as children, a CTA into
 * the actual product, and the same visible Sources list the citation
 * markup describes. */
export function BlogPostShell({
  entry,
  citations,
  cta,
  children,
}: {
  entry: ContentEntry;
  citations: Citation[];
  cta: { heading: string; body: string; href: string; label: string };
  children: ReactNode;
}) {
  const breadcrumb = breadcrumbJsonLd([
    { name: "Home", path: "/" },
    { name: "Blog", path: "/blog" },
    { name: entry.title },
  ]);
  const article = articleJsonLd({
    path: entry.path,
    headline: entry.title,
    description: entry.description,
    publishedDate: entry.publishedDate,
    updatedDate: entry.updatedDate,
    citations,
  });

  return (
    <main className="min-h-screen px-6 pb-28 pt-8 sm:px-10">
      <JsonLd data={breadcrumb} />
      <JsonLd data={article} />
      <div className="mx-auto max-w-3xl">
        <SiteHeader />

        <div className="mt-10">
          <BreadcrumbNav items={[{ name: "Home", path: "/" }, { name: "Blog", path: "/blog" }, { name: entry.title }]} />
          <h1 className="mt-3 font-serif text-3xl text-ink dark:text-ink-dark sm:text-4xl">
            {entry.title}
          </h1>
          <p className="mt-3 text-[12px] text-ink/50 dark:text-ink-dark/50">
            By{" "}
            <Link href="/about" className="underline decoration-ink/15 underline-offset-4 hover:text-ink/70 dark:hover:text-ink-dark/70">
              {FOUNDER_NAME}
            </Link>{" "}
            · Published {formatDate(entry.publishedDate)}
            {entry.updatedDate !== entry.publishedDate ? ` · Updated ${formatDate(entry.updatedDate)}` : ""}
          </p>
        </div>

        <article className="prose-none mt-10 space-y-6">{children}</article>

        <div className="mt-14 rounded-2xl bg-[#181310] p-8 text-center sm:p-10">
          <p className="font-serif text-xl text-white sm:text-2xl">{cta.heading}</p>
          <p className="mt-2 max-w-md mx-auto text-[13px] leading-relaxed text-white/68">{cta.body}</p>
          <Link
            href={cta.href}
            className="mt-6 inline-block rounded-full bg-white px-6 py-2.5 text-[13px] font-medium text-black transition active:scale-[0.97]"
          >
            {cta.label}
          </Link>
        </div>

        <SourceList sources={citations} />

        <Footer />
      </div>
    </main>
  );
}

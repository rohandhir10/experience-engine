import { SiteHeader } from "@/components/SiteHeader";
import { Footer } from "@/components/Footer";
import { JsonLd } from "@/components/JsonLd";
import { BreadcrumbNav } from "@/components/BreadcrumbNav";
import Link from "next/link";
import { contentByKind } from "@/lib/content";
import { breadcrumbJsonLd, webPageJsonLd } from "@/lib/schema";
import { FOUNDER_NAME } from "@/lib/seo";

const posts = contentByKind("blog").slice().sort((a, b) => (a.publishedDate < b.publishedDate ? 1 : -1));

export const metadata = {
  title: "Blog",
  description:
    "Research-grounded writing on translation, localization, and what makes a lyric or a comic line's adaptation actually good.",
  alternates: { canonical: "/blog" },
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" });
}

export default function BlogIndexPage() {
  const breadcrumb = breadcrumbJsonLd([{ name: "Home", path: "/" }, { name: "Blog" }]);
  const webPage = webPageJsonLd({
    path: "/blog",
    name: "Blog",
    description: metadata.description,
    updatedDate: posts[0]?.updatedDate ?? "2026-08-05",
  });

  return (
    <main className="min-h-screen px-6 pb-28 pt-8 sm:px-10">
      <JsonLd data={breadcrumb} />
      <JsonLd data={webPage} />
      <div className="mx-auto max-w-3xl">
        <SiteHeader />

        <div className="mt-10">
          <BreadcrumbNav items={[{ name: "Home", path: "/" }, { name: "Blog" }]} />
          <h1 className="mt-3 font-serif text-3xl text-ink dark:text-ink-dark sm:text-4xl">
            Blog.
          </h1>
          <p className="mt-4 max-w-prose text-[15px] leading-relaxed text-ink/55 dark:text-ink-dark/55">
            Writing on translation and localization research, grounded in
            real sources - not marketing copy dressed up as an article.
            Also see the{" "}
            <Link href="/glossary" className="underline decoration-ink/20 underline-offset-4">
              glossary
            </Link>{" "}
            for definitions of the terms used here.
          </p>
        </div>

        <div className="mt-12 space-y-8">
          {posts.map((post) => (
            <Link
              key={post.slug}
              href={post.path}
              className="block border-b border-black/[0.10] pb-8 transition hover:opacity-70 dark:border-white/[0.11]"
            >
              <p className="text-[12px] text-ink/35 dark:text-ink-dark/35">
                By {FOUNDER_NAME} · {formatDate(post.publishedDate)}
              </p>
              <h2 className="mt-2 font-serif text-lg text-ink dark:text-ink-dark">{post.title}</h2>
              <p className="mt-2 max-w-prose text-[14px] leading-relaxed text-ink/60 dark:text-ink-dark/60">
                {post.description}
              </p>
            </Link>
          ))}
        </div>

        <Footer />
      </div>
    </main>
  );
}

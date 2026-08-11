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

// A light editorial categorization, not new claims about the posts
// themselves - every post already exists in lib/content.ts's registry,
// this just labels which corner of the site's subject matter each one
// falls into so the hub reads as organized sections instead of one
// undifferentiated list. Keyed by slug rather than added as a field on
// ContentEntry itself, since sitemap.ts/JSON-LD/every other consumer of
// that registry has no use for a topic label - scoping it here keeps
// the shared type from growing a field only this one page reads.
type Topic = "music" | "comics" | "craft";
const TOPICS: Record<string, Topic> = {
  "why-literal-translation-breaks-song-lyrics": "music",
  "what-manga-localization-actually-costs": "comics",
  "why-bleu-score-cant-judge-creative-translation": "craft",
  "what-transcreation-means": "craft",
};

const TOPIC_META: Record<Topic, { label: string; Icon: () => JSX.Element }> = {
  music: { label: "Music", Icon: MusicIcon },
  comics: { label: "Comics", Icon: CommentIcon },
  craft: { label: "Craft & research", Icon: CompassIcon },
};

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
      <div className="mx-auto max-w-4xl">
        <SiteHeader />

        <div className="mt-10 max-w-2xl">
          <BreadcrumbNav items={[{ name: "Home", path: "/" }, { name: "Blog" }]} />
          <h1 className="mt-3 font-serif text-3xl text-ink dark:text-ink-dark sm:text-4xl">
            Blog.
          </h1>
          <p className="mt-4 max-w-prose text-[15px] leading-relaxed text-ink/70 dark:text-ink-dark/70">
            Writing on translation and localization research, grounded in
            real sources - not marketing copy dressed up as an article.
            Also see the{" "}
            <Link href="/glossary" className="underline decoration-ink/20 underline-offset-4">
              glossary
            </Link>{" "}
            for definitions of the terms used here.
          </p>
        </div>

        <div className="mt-10 grid grid-cols-1 gap-5 sm:grid-cols-2">
          {posts.map((post) => {
            const topic = TOPICS[post.slug] ?? "craft";
            const { label, Icon } = TOPIC_META[topic];
            return (
              <Link
                key={post.slug}
                href={post.path}
                className="group flex flex-col rounded-2xl border border-black/[0.12] bg-black/[0.015] p-6 transition-all duration-300 hover:-translate-y-1 hover:border-black/[0.18] hover:bg-black/[0.03] hover:shadow-[0_24px_48px_-24px_rgba(0,0,0,0.15)] dark:border-white/10 dark:bg-white/[0.03] dark:hover:border-white/20 dark:hover:bg-white/[0.05] dark:hover:shadow-[0_24px_48px_-24px_rgba(0,0,0,0.6)]"
              >
                <div className="flex items-center gap-2">
                  <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent/10 text-accent">
                    <Icon />
                  </span>
                  <span className="text-[11px] font-medium uppercase tracking-[0.08em] text-accent">
                    {label}
                  </span>
                </div>
                <h2 className="mt-4 font-serif text-[1.15rem] leading-snug text-ink dark:text-ink-dark">
                  {post.title}
                </h2>
                <p className="mt-2 flex-1 text-[13.5px] leading-relaxed text-ink/70 dark:text-ink-dark/70">
                  {post.description}
                </p>
                <div className="mt-5 flex items-center justify-between border-t border-black/[0.08] pt-3 text-[12px] text-ink/50 dark:border-white/10 dark:text-ink-dark/50">
                  <span>By {FOUNDER_NAME}</span>
                  <span>{formatDate(post.publishedDate)}</span>
                </div>
              </Link>
            );
          })}
        </div>

        <Footer />
      </div>
    </main>
  );
}

function MusicIcon() {
  return (
    <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 18V5l12-2v13M9 18a3 3 0 11-6 0 3 3 0 016 0zm12-2a3 3 0 11-6 0 3 3 0 016 0z" />
    </svg>
  );
}

function CommentIcon() {
  return (
    <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 4h16v12H7l-3 3V4z" />
    </svg>
  );
}

function CompassIcon() {
  return (
    <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="9" />
      <path d="M14.5 9.5 13 13l-3.5 1.5L11 11l3.5-1.5z" />
    </svg>
  );
}

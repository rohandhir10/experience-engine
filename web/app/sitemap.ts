import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/seo";
import { CONTENT_REGISTRY } from "@/lib/content";

// Only real, indexable marketing/product pages - deliberately excludes
// /dashboard/* (private, noindex), /sign-in (thin utility page, noindex),
// and /alternate-homepage (an internal draft layout, noindex, not meant
// to be found via search). Static routes use the actual build time (this
// project has no way to track their per-page edit history); editorial
// content (blog/compare/landing/glossary) uses its own real updatedDate
// from lib/content.ts - the same date the biweekly refresh Routine bumps
// when it actually edits a page, so lastModified never claims a change
// that didn't happen.
export default function sitemap(): MetadataRoute.Sitemap {
  const lastModified = new Date();
  const routes = [
    { path: "/", priority: 1 },
    { path: "/music", priority: 0.9 },
    { path: "/comics", priority: 0.9 },
    { path: "/how-it-works", priority: 0.8 },
    { path: "/faq", priority: 0.8 },
    { path: "/about", priority: 0.5 },
    { path: "/blog", priority: 0.7 },
    { path: "/pricing", priority: 0.7 },
    { path: "/s/demo", priority: 0.5 },
  ];

  const staticEntries = routes.map(({ path, priority }) => ({
    url: `${SITE_URL}${path}`,
    lastModified,
    priority,
  }));

  const priorityByKind: Record<string, number> = {
    landing: 0.8,
    guide: 0.75,
    glossary: 0.7,
    blog: 0.6,
    compare: 0.6,
  };

  const contentEntries = CONTENT_REGISTRY.map((entry) => ({
    url: `${SITE_URL}${entry.path}`,
    lastModified: new Date(entry.updatedDate),
    priority: priorityByKind[entry.kind],
  }));

  return [...staticEntries, ...contentEntries];
}

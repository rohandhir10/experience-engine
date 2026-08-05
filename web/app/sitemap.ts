import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/seo";

// Only real, indexable marketing/product pages - deliberately excludes
// /dashboard/* (private, noindex), /sign-in (thin utility page, noindex),
// and /alternate-homepage (an internal draft layout, noindex, not meant
// to be found via search). lastModified is the actual build time, not a
// fabricated per-page edit date this project has no way to track yet.
export default function sitemap(): MetadataRoute.Sitemap {
  const lastModified = new Date();
  const routes = [
    { path: "/", priority: 1 },
    { path: "/music", priority: 0.9 },
    { path: "/comics", priority: 0.9 },
    { path: "/how-it-works", priority: 0.8 },
    { path: "/faq", priority: 0.8 },
    { path: "/pricing", priority: 0.7 },
    { path: "/s/demo", priority: 0.5 },
  ];

  return routes.map(({ path, priority }) => ({
    url: `${SITE_URL}${path}`,
    lastModified,
    priority,
  }));
}

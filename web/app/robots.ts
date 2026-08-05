import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/seo";

// Explicitly allowing known AI answer-engine/training crawlers (rather
// than relying on the default catch-all `*` rule to cover them) is the
// actual mechanism behind "generative engine optimization" - being
// citable by ChatGPT/Perplexity/Google's AI Overviews requires those
// crawlers to be able to fetch the site at all. /dashboard and
// account-scoped /api routes are disallowed: private, non-indexable,
// and would only appear as broken/empty pages to a crawler anyway.
export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: ["/dashboard", "/api", "/sign-in"],
      },
      { userAgent: "GPTBot", allow: "/" },
      { userAgent: "ChatGPT-User", allow: "/" },
      { userAgent: "Google-Extended", allow: "/" },
      { userAgent: "PerplexityBot", allow: "/" },
      { userAgent: "ClaudeBot", allow: "/" },
      { userAgent: "anthropic-ai", allow: "/" },
      { userAgent: "CCBot", allow: "/" },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}

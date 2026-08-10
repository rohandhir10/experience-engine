// Single source of truth for the site's real production origin, used to
// build absolute URLs for canonical tags, OG/Twitter metadata, sitemap.xml,
// robots.txt, and JSON-LD @id/url fields. usecastia.com is the domain
// decided on for this product; metadata is built against it even before
// DNS/deploy are pointed there, the same way you write an address on an
// envelope before the recipient has moved in.
export const SITE_URL = "https://usecastia.com";
export const SITE_NAME = "Castia";

// The one real named person behind this site - used as the Person author
// on editorial content (lib/schema.ts's articleJsonLd) and the
// Organization's `founder` field (app/layout.tsx), instead of every page
// attributing authorship to the faceless "Castia" organization. See
// app/about/page.tsx for the one place this gets a real bio, kept
// deliberately minimal - no invented backstory or credentials.
export const FOUNDER_NAME = "Rohan Dhir";

export function absoluteUrl(path: string): string {
  return new URL(path, SITE_URL).toString();
}

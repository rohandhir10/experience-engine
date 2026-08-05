// Single source of truth for the site's real production origin, used to
// build absolute URLs for canonical tags, OG/Twitter metadata, sitemap.xml,
// robots.txt, and JSON-LD @id/url fields. usecastia.com is the domain
// decided on for this product; metadata is built against it even before
// DNS/deploy are pointed there, the same way you write an address on an
// envelope before the recipient has moved in.
export const SITE_URL = "https://usecastia.com";
export const SITE_NAME = "Castia";

export function absoluteUrl(path: string): string {
  return new URL(path, SITE_URL).toString();
}

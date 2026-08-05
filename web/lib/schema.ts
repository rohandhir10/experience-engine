import { SITE_NAME, absoluteUrl } from "./seo";

// Shared JSON-LD builders so every editorial page emits the same shape
// (and the same real dates from lib/content.ts) instead of each page
// hand-rolling its own schema and drifting out of sync.

export function breadcrumbJsonLd(items: { name: string; path?: string }[]) {
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: items.map((item, index) => ({
      "@type": "ListItem",
      position: index + 1,
      name: item.name,
      ...(item.path ? { item: absoluteUrl(item.path) } : {}),
    })),
  };
}

export type Citation = { name: string; url: string };

export function articleJsonLd({
  path,
  headline,
  description,
  publishedDate,
  updatedDate,
  citations,
}: {
  path: string;
  headline: string;
  description: string;
  publishedDate: string;
  updatedDate: string;
  citations?: Citation[];
}) {
  return {
    "@context": "https://schema.org",
    "@type": "Article",
    "@id": absoluteUrl(path),
    mainEntityOfPage: absoluteUrl(path),
    headline,
    description,
    datePublished: publishedDate,
    dateModified: updatedDate,
    author: { "@type": "Organization", name: SITE_NAME, url: absoluteUrl("/") },
    publisher: { "@type": "Organization", name: SITE_NAME, url: absoluteUrl("/") },
    ...(citations && citations.length > 0
      ? { citation: citations.map((c) => ({ "@type": "CreativeWork", name: c.name, url: c.url })) }
      : {}),
  };
}

export function webPageJsonLd({
  path,
  name,
  description,
  updatedDate,
}: {
  path: string;
  name: string;
  description: string;
  updatedDate: string;
}) {
  return {
    "@context": "https://schema.org",
    "@type": "WebPage",
    "@id": absoluteUrl(path),
    url: absoluteUrl(path),
    name,
    description,
    dateModified: updatedDate,
    isPartOf: { "@type": "WebSite", name: SITE_NAME, url: absoluteUrl("/") },
  };
}

export function definedTermSetJsonLd({
  path,
  name,
  description,
  terms,
}: {
  path: string;
  name: string;
  description: string;
  terms: { term: string; definition: string }[];
}) {
  return {
    "@context": "https://schema.org",
    "@type": "DefinedTermSet",
    "@id": absoluteUrl(path),
    name,
    description,
    hasDefinedTerm: terms.map((t) => ({
      "@type": "DefinedTerm",
      name: t.term,
      description: t.definition,
      inDefinedTermSet: absoluteUrl(path),
    })),
  };
}

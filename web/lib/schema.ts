import { SITE_NAME, FOUNDER_NAME, absoluteUrl } from "./seo";

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
    author: { "@type": "Person", name: FOUNDER_NAME, url: absoluteUrl("/about") },
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

export function howToJsonLd({
  path,
  name,
  description,
  steps,
}: {
  path: string;
  name: string;
  description: string;
  steps: { name: string; text: string }[];
}) {
  return {
    "@context": "https://schema.org",
    "@type": "HowTo",
    "@id": `${absoluteUrl(path)}#howto`,
    name,
    description,
    step: steps.map((s, index) => ({
      "@type": "HowToStep",
      position: index + 1,
      name: s.name,
      text: s.text,
    })),
  };
}

export function productJsonLd({
  path,
  name,
  description,
  offers,
  availability,
}: {
  path: string;
  name: string;
  description: string;
  offers: { name: string; price: string; priceCurrency: string; description: string }[];
  /** "https://schema.org/PreOrder" while checkout isn't live yet - must
   * match the page's own visible disclosure, never claim InStock ahead
   * of it actually being purchasable. */
  availability?: string;
}) {
  return {
    "@context": "https://schema.org",
    "@type": "Product",
    "@id": absoluteUrl(path),
    name,
    description,
    brand: { "@type": "Brand", name: SITE_NAME },
    offers: offers.map((o) => ({
      "@type": "Offer",
      name: o.name,
      price: o.price,
      priceCurrency: o.priceCurrency,
      description: o.description,
      url: absoluteUrl(path),
      ...(availability ? { availability } : {}),
    })),
  };
}

// For /music and /comics specifically - the two actual interactive
// tools, not marketing pages about them. Distinct from the sitewide
// SoftwareApplication in app/layout.tsx (which describes the product as
// a whole); this is the real, more specific WebApplication type Google's
// structured-data docs recommend for a single in-browser tool page, so
// each carries its own name/description/URL instead of only inheriting
// the site-level one. Reuses the same real free-tier fact from layout.tsx
// rather than restating a different, unverified offer.
export function webApplicationJsonLd({
  path,
  name,
  description,
}: {
  path: string;
  name: string;
  description: string;
}) {
  return {
    "@context": "https://schema.org",
    "@type": "WebApplication",
    "@id": absoluteUrl(path),
    name,
    url: absoluteUrl(path),
    description,
    applicationCategory: "MultimediaApplication",
    operatingSystem: "Web",
    offers: {
      "@type": "Offer",
      price: "0",
      priceCurrency: "USD",
      description: "Free tier - a limited number of adaptations per day, no account required.",
    },
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
    publisher: { "@type": "Organization", name: SITE_NAME, url: absoluteUrl("/") },
    hasDefinedTerm: terms.map((t) => ({
      "@type": "DefinedTerm",
      name: t.term,
      description: t.definition,
      inDefinedTermSet: absoluteUrl(path),
    })),
  };
}

// Shared by app/faq/page.tsx (the full list) and app/page.tsx (a
// curated subset) - see lib/faqs.ts for why the underlying text is a
// single array too. Visible content and this markup must always be the
// exact same strings, which is why both callers pass Faq objects
// straight from that one array rather than re-typing any answer.
export function faqPageJsonLd(faqs: { question: string; answer: string }[]) {
  return {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: faqs.map((faq) => ({
      "@type": "Question",
      name: faq.question,
      acceptedAnswer: {
        "@type": "Answer",
        text: faq.answer,
      },
    })),
  };
}

import type { Metadata } from "next";
import { JsonLd } from "@/components/JsonLd";
import { breadcrumbJsonLd, faqPageJsonLd, webApplicationJsonLd } from "@/lib/schema";
import { comicsFaqs } from "@/lib/faqs";

export const metadata: Metadata = {
  title: "Adapt webtoon and comic dialogue (Beta)",
  description:
    "Upload comic or webtoon panels. Castia OCRs each bubble, adapts the dialogue through the same Writers' Room pipeline as its music tool, and can redraw the panel with the adapted text typeset in. Beta: sound-effect text over artwork isn't redrawn yet.",
  alternates: { canonical: "/comics" },
  openGraph: {
    title: "Castia — Adapt webtoon and comic dialogue (Beta)",
    description:
      "Upload comic or webtoon panels. Castia OCRs each bubble and adapts the dialogue through the same Writers' Room pipeline as its music tool.",
    url: "/comics",
  },
};

// Same real gap as app/music/layout.tsx - /comics is the second actual
// product tool and had no page-specific JSON-LD at all.
export default function ComicsLayout({ children }: { children: React.ReactNode }) {
  const breadcrumb = breadcrumbJsonLd([{ name: "Home", path: "/" }, { name: "Webtoons" }]);
  const webApplication = webApplicationJsonLd({
    path: "/comics",
    name: "Castia — Webtoons (Beta)",
    description: metadata.description as string,
  });
  // Matches the visible "Common questions" section app/comics/page.tsx
  // renders in its own empty state (before any panel is uploaded) - a
  // crawler or a fresh visitor always sees that empty state first, so
  // this is never claiming markup for content nobody's page load shows.
  const faqPage = faqPageJsonLd(comicsFaqs());
  return (
    <>
      <JsonLd data={breadcrumb} />
      <JsonLd data={webApplication} />
      <JsonLd data={faqPage} />
      {children}
    </>
  );
}

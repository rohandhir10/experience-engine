import type { Metadata } from "next";
import { JsonLd } from "@/components/JsonLd";
import { breadcrumbJsonLd, faqPageJsonLd, webApplicationJsonLd } from "@/lib/schema";
import { comicsFaqs } from "@/lib/faqs";

// The "(Beta)" suffix that used to sit on this page's <title>/OG title/
// JSON-LD name is gone (real feedback that the badge/tag reads as
// clutter, same call as the visual pill on the tile and hero below) -
// the gap it flagged is still real and still fully stated in the
// description right here, just not repeated as a tag on every title
// string too.
export const metadata: Metadata = {
  title: "Adapt webtoon and comic dialogue",
  description:
    "Upload comic or webtoon panels. CASTIA detects dialogue in each bubble, adapts it with character voice and scene context in mind, and can redraw panels with adapted text typeset in. Sound-effect text over artwork isn't redrawn yet.",
  alternates: { canonical: "/comics" },
  openGraph: {
    title: "Castia — Adapt webtoon and comic dialogue",
    description:
      "Upload comic or webtoon panels. CASTIA detects each dialogue bubble and adapts it with character voice, emotional intent, and panel context in mind.",
    url: "/comics",
  },
};

// Same real gap as app/music/layout.tsx - /comics is the second actual
// product tool and had no page-specific JSON-LD at all.
export default function ComicsLayout({ children }: { children: React.ReactNode }) {
  const breadcrumb = breadcrumbJsonLd([{ name: "Home", path: "/" }, { name: "Webtoons" }]);
  const webApplication = webApplicationJsonLd({
    path: "/comics",
    name: "Castia — Webtoons",
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

import type { Metadata } from "next";
import { JsonLd } from "@/components/JsonLd";
import { breadcrumbJsonLd, faqPageJsonLd, webApplicationJsonLd } from "@/lib/schema";
import { musicFaqs } from "@/lib/faqs";

export const metadata: Metadata = {
  title: "Adapt song lyrics across six languages",
  description:
    "Paste lyrics or import a YouTube link. Castia adapts English, Hindi, Japanese, Korean, Spanish, and Urdu song lyrics in any direction through a three-stage Writers' Room, not a literal translation.",
  alternates: { canonical: "/music" },
  openGraph: {
    title: "Castia — Adapt song lyrics across six languages",
    description:
      "Paste lyrics or import a YouTube link. Castia adapts song lyrics across six languages through a three-stage Writers' Room, not a literal translation.",
    url: "/music",
  },
};

// Real structured-data gap this closed: /music is the actual product -
// the highest-traffic page on the site - and previously carried no
// page-specific JSON-LD at all, only the sitewide Organization/
// SoftwareApplication in app/layout.tsx. A dedicated layout.tsx (rather
// than the page itself, which is a client component and can't export
// metadata or run this server-side) is the right place for it.
export default function MusicLayout({ children }: { children: React.ReactNode }) {
  const breadcrumb = breadcrumbJsonLd([{ name: "Home", path: "/" }, { name: "Music" }]);
  const webApplication = webApplicationJsonLd({
    path: "/music",
    name: "Castia — Music",
    description: metadata.description as string,
  });
  // The visible "Common questions" section InputScreen.tsx renders near
  // its own footer uses this exact same musicFaqs() call - same
  // reasoning as app/page.tsx's homepage FAQ block: markup and visible
  // text have to be the same real strings, so both read from the one
  // shared array in lib/faqs.ts rather than each typing its own copy.
  const faqPage = faqPageJsonLd(musicFaqs());
  return (
    <>
      <JsonLd data={breadcrumb} />
      <JsonLd data={webApplication} />
      <JsonLd data={faqPage} />
      {children}
    </>
  );
}

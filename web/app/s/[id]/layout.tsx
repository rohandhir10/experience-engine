import type { Metadata } from "next";
import { JsonLd } from "@/components/JsonLd";
import { breadcrumbJsonLd } from "@/lib/schema";
import { absoluteUrl, SITE_NAME } from "@/lib/seo";
import { demoResult } from "@/lib/demo-data";

// Real structured-data/metadata gap this closed: /s/[id] (a shared
// adaptation result - the whole point of a share link) had NO metadata
// at all, not even a title - every shared link inherited the generic
// site-wide default and looked identical in a search result or social
// preview regardless of what was actually shared.
//
// The honest limit: result content for an arbitrary id is only known
// client-side (sessionStorage or a network fetch in page.tsx, see its
// own comment on why) - there's no server-side access to it here, so a
// real per-result title/description/JSON-LD isn't possible for most
// ids without a larger architecture change. id === "demo" is the one
// exception: it's the single result this project has fully reviewed for
// accuracy (see public/llms.txt's citation notes) and its content is a
// real static import, available server-side - so that one case gets a
// real, specific title, description, and CreativeWork JSON-LD. Every
// other id gets an honest, generic-but-accurate description instead of
// either nothing or an invented specific.
export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  if (id === "demo") {
    const title = "A worked example: Hindi to English lyric adaptation";
    const description = demoResult.hook;
    return {
      title,
      description,
      alternates: { canonical: "/s/demo" },
      openGraph: { title: `${title} | ${SITE_NAME}`, description, url: "/s/demo" },
    };
  }
  return {
    title: "A shared adaptation",
    description:
      "A song lyric adapted by Castia - the literal translation, the adapted line, and the reasoning behind it, shown side by side.",
    robots: { index: false, follow: true },
  };
}

export default async function SharedResultLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const isDemo = id === "demo";
  const breadcrumb = breadcrumbJsonLd([{ name: "Home", path: "/" }, { name: "Worked example" }]);
  const creativeWork = isDemo
    ? {
        "@context": "https://schema.org",
        "@type": "CreativeWork",
        "@id": absoluteUrl("/s/demo"),
        url: absoluteUrl("/s/demo"),
        name: "A worked example: Hindi to English lyric adaptation",
        description: demoResult.hook,
        inLanguage: demoResult.targetLanguage,
        translationOfWork: { "@type": "CreativeWork", inLanguage: demoResult.sourceLanguage },
        author: { "@type": "Organization", name: SITE_NAME, url: absoluteUrl("/") },
      }
    : null;
  return (
    <>
      {isDemo && (
        <>
          <JsonLd data={breadcrumb} />
          <JsonLd data={creativeWork!} />
        </>
      )}
      {children}
    </>
  );
}

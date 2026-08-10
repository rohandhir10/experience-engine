import type { Metadata } from "next";
import Script from "next/script";
import "./globals.css";
import { AmbientGlow } from "@/components/AmbientGlow";
import { JsonLd } from "@/components/JsonLd";
import { SessionProviderWrapper } from "@/components/SessionProviderWrapper";
import { SITE_URL, SITE_NAME, FOUNDER_NAME, absoluteUrl } from "@/lib/seo";
import { THEME_INIT_SCRIPT } from "@/lib/theme";

const DEFAULT_TITLE = "Castia — Adapt the feeling, not just the words";
const DEFAULT_DESCRIPTION =
  "Castia rewrites song lyrics and comic dialogue across six languages through a three-stage Writers' Room (Translator, Creative Adapter, Judge) — not a literal translation, and every change ships with a plain-language reason.";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: DEFAULT_TITLE,
    template: `%s | ${SITE_NAME}`,
  },
  description: DEFAULT_DESCRIPTION,
  alternates: {
    canonical: "/",
  },
  openGraph: {
    type: "website",
    siteName: SITE_NAME,
    url: SITE_URL,
    title: DEFAULT_TITLE,
    description: DEFAULT_DESCRIPTION,
  },
  twitter: {
    card: "summary_large_image",
    title: DEFAULT_TITLE,
    description: DEFAULT_DESCRIPTION,
  },
};

// Site-wide structured data: two real, verifiable facts about the
// organization/product, not a marketing claim dressed up as schema.
// Deliberately no `aggregateRating` (no real reviews exist) and no
// `offers` for a paid tier (billing isn't live yet, per /pricing) - only
// the Free tier's real $0 price is honest to publish. See
// docs/CAPABILITY_MATRIX.md for the "no fabricated capability, screenshot,
// or data" rule this follows.
const organizationJsonLd = {
  "@context": "https://schema.org",
  "@type": "Organization",
  name: SITE_NAME,
  url: SITE_URL,
  logo: absoluteUrl("/logo"),
  founder: { "@type": "Person", name: FOUNDER_NAME, url: absoluteUrl("/about") },
};

const softwareApplicationJsonLd = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: SITE_NAME,
  url: SITE_URL,
  applicationCategory: "MultimediaApplication",
  operatingSystem: "Web",
  description: DEFAULT_DESCRIPTION,
  offers: {
    "@type": "Offer",
    price: "0",
    priceCurrency: "USD",
    description: "Free tier - a limited number of adaptations per day, no account required.",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="font-sans bg-paper text-ink dark:bg-paper-dark dark:text-ink-dark antialiased">
        {/* Sets the `dark` class on <html> before hydration - beforeInteractive
            runs it as part of the initial HTML, ahead of paint, so there's no
            flash of the wrong theme. suppressHydrationWarning above covers the
            <html> element since this script mutates its class/style attributes
            outside React's own render. */}
        <Script id="theme-init" strategy="beforeInteractive">
          {THEME_INIT_SCRIPT}
        </Script>
        <JsonLd data={organizationJsonLd} />
        <JsonLd data={softwareApplicationJsonLd} />
        <AmbientGlow />
        <SessionProviderWrapper>{children}</SessionProviderWrapper>
      </body>
    </html>
  );
}

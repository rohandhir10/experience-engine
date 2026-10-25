import type { Metadata } from "next";
import { headers } from "next/headers";
import "./globals.css";
import "./site-theme.css";
import { AmbientGlow } from "@/components/AmbientGlow";
import { JsonLd } from "@/components/JsonLd";
import { SessionProviderWrapper } from "@/components/SessionProviderWrapper";
import { SITE_URL, SITE_NAME, FOUNDER_NAME, absoluteUrl } from "@/lib/seo";
import { THEME_INIT_SCRIPT } from "@/lib/theme";

const DEFAULT_TITLE = "CASTIA — Every panel. Every feeling. Every language.";
const DEFAULT_DESCRIPTION =
  "CASTIA helps webtoon and comic localization teams preserve character voice, emotional intent, cultural nuance, and panel context across languages.";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: { default: DEFAULT_TITLE, template: `%s | ${SITE_NAME}` },
  description: DEFAULT_DESCRIPTION,
  alternates: { canonical: "/" },
  openGraph: { type: "website", siteName: SITE_NAME, url: SITE_URL, title: DEFAULT_TITLE, description: DEFAULT_DESCRIPTION },
  twitter: { card: "summary_large_image", title: DEFAULT_TITLE, description: DEFAULT_DESCRIPTION },
};

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

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const nonce = (await headers()).get("x-nonce") ?? undefined;

  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
      </head>
      <body className="font-sans bg-paper text-ink dark:bg-paper-dark dark:text-ink-dark antialiased">
        <script id="theme-init" nonce={nonce} dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
        <JsonLd data={organizationJsonLd} />
        <JsonLd data={softwareApplicationJsonLd} />
        <AmbientGlow />
        <SessionProviderWrapper>{children}</SessionProviderWrapper>
      </body>
    </html>
  );
}

import type { Metadata } from "next";

// Same real gap as app/s/[id]/layout.tsx: this share page had no
// metadata at all. No comics equivalent of demo-data.ts exists, so
// unlike the music share page there's no server-accessible real result
// to build a specific title/description from for any id - an honest
// generic description plus noindex (this is dynamic, client-fetched
// content the server can't verify) is what's actually true here, not a
// per-result claim this layout has no way to check.
export const metadata: Metadata = {
  // Hardcoded suffix, not left to the root layout's title template: two
  // levels of plain-string title down from root (comics/layout.tsx, then
  // this one) stops that template from reaching this deep - confirmed by
  // comparing this page's rendered <title> against /comics's own, which
  // does get the "| Castia" suffix from being only one level down.
  title: "A shared adaptation | Castia",
  description:
    "A comic or webtoon panel adapted by Castia - the original dialogue, the adapted line, and the reasoning behind it.",
  robots: { index: false, follow: true },
};

export default function ComicsSharedResultLayout({ children }: { children: React.ReactNode }) {
  return children;
}

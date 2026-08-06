import type { Metadata } from "next";

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

export default function ComicsLayout({ children }: { children: React.ReactNode }) {
  return children;
}

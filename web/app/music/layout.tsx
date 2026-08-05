import type { Metadata } from "next";

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

export default function MusicLayout({ children }: { children: React.ReactNode }) {
  return children;
}

import type { Metadata } from "next";
import "./globals.css";
import { AmbientGlow } from "@/components/AmbientGlow";

export const metadata: Metadata = {
  title: "CASTIA — Feel the song again",
  description:
    "Paste a song. CASTIA gives you back the version that means what it feels like to those who already understand it.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="font-sans bg-paper text-ink dark:bg-paper-dark dark:text-ink-dark antialiased">
        <AmbientGlow />
        {children}
      </body>
    </html>
  );
}

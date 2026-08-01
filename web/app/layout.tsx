import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AURA — Feel the song again",
  description:
    "Paste a song. AURA gives you back the version that means what it feels like to those who already understand it.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="font-sans bg-paper text-ink dark:bg-paper-dark dark:text-ink-dark antialiased">
        {children}
      </body>
    </html>
  );
}

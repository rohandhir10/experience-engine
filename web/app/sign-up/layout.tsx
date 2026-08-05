import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Sign Up",
  description: "Create a Castia account to keep a history of every song and comic you adapt.",
  robots: { index: false, follow: true },
  alternates: { canonical: "/sign-up" },
};

export default function SignUpLayout({ children }: { children: React.ReactNode }) {
  return children;
}

import type { Metadata } from "next";

// Applies to every /dashboard/* route: signed-in, personalized, no
// content of value to a search crawler, and indexing it would only ever
// surface an empty/sign-in-prompt state to searchers who aren't logged
// in as that specific user.
export const metadata: Metadata = {
  title: "Dashboard",
  robots: { index: false, follow: false },
};

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return children;
}

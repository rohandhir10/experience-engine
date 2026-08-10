import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { auth } from "@/auth";

// Applies to every /dashboard/* route: signed-in, personalized, no
// content of value to a search crawler, and indexing it would only ever
// surface an empty/sign-in-prompt state to searchers who aren't logged
// in as that specific user.
export const metadata: Metadata = {
  title: "Dashboard",
  robots: { index: false, follow: false },
};

// Real gate, not just a documented intent - every /dashboard/* page is
// a server component (only app/dashboard/page.tsx itself is a client
// component, and it's a child of this layout, so this still runs
// first). Before this existed, a signed-out visitor who followed a
// bookmark or an old link got the FULL page - header, sidebar, page
// title - around whichever small "Sign in to keep..." prompt that
// page's own data-fetching component (RecentAdaptations, CreditLedger,
// ApiKeysManager) happened to render, with real 401s hitting the
// console underneath it. One check here, before any of that renders,
// same "auth() in a layout guards every nested route" pattern
// Auth.js/Next.js document for exactly this case.
//
// auth() is wrapped in .catch(() => null) - same defensive pattern
// app/sign-in/page.tsx already uses - since a deployment with no
// AUTH_SECRET configured at all throws MissingSecret rather than
// returning an empty session; that's still correctly "not signed in"
// here, and /sign-in's own `configured` check already explains that
// case honestly rather than pretending an account system exists.
export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const session = await auth().catch(() => null);
  if (!session?.castiaUserId) {
    redirect("/sign-in");
  }
  return children;
}

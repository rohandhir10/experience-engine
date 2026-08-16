"use client";

import { signOut, useSession } from "next-auth/react";

/** Who you're signed in as, and the way out - at the bottom of the
 * dashboard sidebar.
 *
 * Both halves were missing entirely before this existed, found by
 * actually walking the signed-in app in a browser rather than reading
 * the code: not one of the seven /dashboard/* pages had any sign-out
 * control, and SiteHeader still renders "Sign In" / "Get Started" to a
 * signed-in visitor on every page (a deliberate tradeoff it documents -
 * it's rendered from both server and client trees, so it can't read the
 * session without a broader refactor). The combined effect was that the
 * only sign-out button in the whole app lived on /sign-in, which a
 * signed-in user could only reach by clicking a link labelled "Sign
 * In" - and nothing anywhere told them which account they were using.
 *
 * A client component for the same reason MediumSwitcher/UseCasesMenu
 * are: DashboardSidebar itself is imported by app/dashboard/page.tsx,
 * which is "use client", so the sidebar can't become async or hold a
 * server action. useSession() needs no prop threading through five
 * server pages and one client page, and SessionProvider is already
 * mounted app-wide (components/SessionProviderWrapper.tsx). Same
 * signOut()/useSession() pairing components/AccountDataControls.tsx
 * already uses.
 *
 * Renders nothing at all when there's no session rather than an empty
 * shell: every /dashboard/* route is already gated by
 * app/dashboard/layout.tsx, so "no session" here means the session is
 * still loading, not that a signed-out person is looking at it. */
export function DashboardAccountPanel() {
  const { data: session } = useSession();
  const email = session?.user?.email;

  if (!email) return null;

  return (
    <div className="mt-2 border-t border-black/[0.09] pt-3 dark:border-white/[0.09]">
      <p className="px-3 text-[11px] uppercase tracking-wide text-ink/68 dark:text-ink-dark/68">
        Signed in as
      </p>
      {/* break-all, not truncate - a long address should wrap and stay
          readable in a 12rem sidebar rather than silently lose its
          domain behind an ellipsis, which is exactly the part that
          tells two accounts apart. */}
      <p className="mt-0.5 break-all px-3 text-[12px] text-ink/80 dark:text-ink-dark/80">
        {email}
      </p>
      <button
        type="button"
        onClick={() => void signOut({ callbackUrl: "/" })}
        className="mt-2 w-full rounded-lg px-3 py-2 text-left text-[13px] text-ink/75 transition hover:bg-black/[0.04] hover:text-ink dark:text-ink-dark/75 dark:hover:bg-white/[0.06] dark:hover:text-ink-dark"
      >
        Sign out
      </button>
    </div>
  );
}

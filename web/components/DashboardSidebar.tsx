import Link from "next/link";
import { DashboardAccountPanel } from "./DashboardAccountPanel";

type DashboardSection =
  | "home"
  | "adaptations"
  | "favorites"
  | "collections"
  | "usage"
  | "settings"
  | "billing";

const NAV_ITEMS: { key: DashboardSection; label: string; href: string }[] = [
  { key: "home", label: "Home", href: "/dashboard" },
  { key: "adaptations", label: "Adaptations", href: "/dashboard/adaptations" },
  { key: "favorites", label: "Favorites", href: "/dashboard/favorites" },
  { key: "collections", label: "Collections", href: "/dashboard/collections" },
  { key: "usage", label: "Usage", href: "/dashboard/usage" },
  // Labeled "API Keys," not "Settings" - that's the only thing this page
  // actually manages (no profile/password/email/account-deletion page
  // exists anywhere in this app yet), and "Settings" promised more than
  // it delivered. The "Beta" badge that used to sit on this row is gone
  // (real feedback that it read as clutter) - the gap it disclosed
  // (server/main.py's /v1/* routes still lack an async job/poll pattern
  // for a long chapter) is still real and still stated in prose on
  // /docs/api, just not flagged with a badge here.
  { key: "settings", label: "API Keys", href: "/dashboard/settings" },
];

const BOTTOM_ITEMS: { key: DashboardSection; label: string; href: string }[] = [
  { key: "billing", label: "Billing", href: "/dashboard/billing" },
];

// Sections that are actually implemented. Everything else still leads to
// an honest DashboardStub and keeps its "Soon" tag — this set is what
// keeps the tag truthful as features land one at a time.
const LIVE_SECTIONS: ReadonlySet<DashboardSection> = new Set<DashboardSection>([
  "home",
  // Real now too (app/dashboard/adaptations/page.tsx's own comment: "no
  // longer a DashboardStub") - the same RecentAdaptations component
  // Favorites already uses, just unfiltered. This set was never updated
  // when that landed, so the nav kept showing "Soon" on a fully working
  // page - found auditing this file for the opposite kind of drift.
  "adaptations",
  "favorites",
  "collections",
  // API key management (server/api_keys.py) is real now - the only real
  // content Settings has today, but real is real.
  "settings",
  // Real balance + ledger history now (server/credits.py's
  // /api/me/credits) - Billing shows purchase history and a buy-more
  // link, Usage shows the debit side of the same ledger. Checkout
  // itself (components/BuyButton.tsx) still degrades until a real
  // Paddle account exists, but the data these pages show is real.
  "billing",
  "usage",
]);

function NavRow({
  label,
  href,
  active,
  live,
}: {
  label: string;
  href: string;
  active: boolean;
  live: boolean;
}) {
  // A not-yet-live section shows "Soon" regardless, unless it's the
  // active row (no point badging the page you're already looking at).
  const shownBadge = !live ? "Soon" : null;
  return (
    <Link
      href={href}
      className={`flex items-center justify-between rounded-lg px-3 py-2 text-[13px] transition ${
        active
          ? "bg-black/[0.04] font-medium text-ink dark:bg-white/[0.06] dark:text-ink-dark"
          : "text-ink/75 hover:text-ink/78 dark:text-ink-dark/75 dark:hover:text-ink-dark/78"
      }`}
    >
      <span>{label}</span>
      {!active && shownBadge && (
        <span className="rounded-full bg-black/[0.05] px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-ink/75 dark:bg-white/10 dark:text-ink-dark/85">
          {shownBadge}
        </span>
      )}
    </Link>
  );
}

/** Every section in LIVE_SECTIONS above is real - adaptation history,
 * starring, grouping, the credit ledger, and API key management (see
 * web/auth.ts, server/accounts.py, server/credits.py,
 * server/api_keys.py). None currently lead to a stub; LIVE_SECTIONS
 * still exists (rather than being deleted now that it covers every
 * DashboardSection) so the next genuinely-unbuilt section has a real
 * place to keep its honest "Soon" tag instead of hiding or faking it,
 * the same convention this app uses elsewhere for a real, disclosed
 * gap. */
export function DashboardSidebar({ active = "home" }: { active?: DashboardSection }) {
  return (
    <nav className="flex w-full flex-col gap-1 sm:w-48 sm:shrink-0">
      {NAV_ITEMS.map((item) => (
        <NavRow
          key={item.key}
          label={item.label}
          href={item.href}
          active={active === item.key}
          live={LIVE_SECTIONS.has(item.key)}
        />
      ))}
      <div className="my-2 border-t border-black/[0.09] dark:border-white/[0.09]" />
      {BOTTOM_ITEMS.map((item) => (
        <NavRow
          key={item.key}
          label={item.label}
          href={item.href}
          active={active === item.key}
          live={LIVE_SECTIONS.has(item.key)}
        />
      ))}
      {/* Which account you're in, and the way out - see that component's
          docstring for why neither existed anywhere in the signed-in app
          before, and why it has to be a client component rather than
          part of this server-renderable one. */}
      <DashboardAccountPanel />
    </nav>
  );
}

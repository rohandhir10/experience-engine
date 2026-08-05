import Link from "next/link";

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
  { key: "settings", label: "Settings", href: "/dashboard/settings" },
];

const BOTTOM_ITEMS: { key: DashboardSection; label: string; href: string }[] = [
  { key: "billing", label: "Billing", href: "/dashboard/billing" },
];

// Sections that are actually implemented. Everything else still leads to
// an honest DashboardStub and keeps its "Soon" tag — this set is what
// keeps the tag truthful as features land one at a time.
const LIVE_SECTIONS: ReadonlySet<DashboardSection> = new Set<DashboardSection>([
  "home",
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
  return (
    <Link
      href={href}
      className={`flex items-center justify-between rounded-lg px-3 py-2 text-[13px] transition ${
        active
          ? "bg-black/[0.04] font-medium text-ink dark:bg-white/[0.06] dark:text-ink-dark"
          : "text-ink/45 hover:text-ink/70 dark:text-ink-dark/45 dark:hover:text-ink-dark/70"
      }`}
    >
      <span>{label}</span>
      {!active && !live && (
        <span className="rounded-full bg-black/[0.05] px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-ink/35 dark:bg-white/10 dark:text-ink-dark/40">
          Soon
        </span>
      )}
    </Link>
  );
}

/** Home, Favorites and Collections are real (adaptation history,
 * starring, and grouping — backed by accounts; see web/auth.ts and
 * server/accounts.py). The remaining sections still lead to honest stubs
 * (components/DashboardStub): there's no usage metering and no settings
 * to change yet. Those keep a "Soon" tag rather than being hidden or inert, so the
 * eventual shape of the product is real to click through without
 * pretending it works — see LIVE_SECTIONS above. */
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
      <div className="my-2 border-t border-black/[0.05] dark:border-white/[0.05]" />
      {BOTTOM_ITEMS.map((item) => (
        <NavRow
          key={item.key}
          label={item.label}
          href={item.href}
          active={active === item.key}
          live={LIVE_SECTIONS.has(item.key)}
        />
      ))}
      {/* server/main.py's /v1/* routes are real now (keys managed on the
          Settings page below) - "Beta" discloses the actual gap
          honestly: no async job/poll pattern for a long chapter, no
          published docs page yet, same convention as Webtoons' own
          "Beta" badge elsewhere in this app. Links to Settings since
          that's where a key is actually issued - there's no separate
          docs page to send this to yet. */}
      <Link
        href="/dashboard/settings"
        className="flex items-center justify-between rounded-lg px-3 py-2 text-[13px] text-ink/30 transition hover:text-ink/55 dark:text-ink-dark/30 dark:hover:text-ink-dark/55"
      >
        <span>API</span>
        <span className="rounded-full bg-black/[0.05] px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-ink/35 dark:bg-white/10 dark:text-ink-dark/40">
          Beta
        </span>
      </Link>
    </nav>
  );
}

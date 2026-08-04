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

/** Home and Favorites are real (adaptation history + starring, backed by
 * accounts — see web/auth.ts and server/accounts.py). The remaining
 * sections still lead to honest stubs (components/DashboardStub): there's
 * no collections storage, no usage metering, and no settings to change
 * yet. Those keep a "Soon" tag rather than being hidden or inert, so the
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
      <div className="flex items-center justify-between px-3 py-2 text-[13px] text-ink/30 dark:text-ink-dark/30">
        <span>API</span>
        <span className="rounded-full bg-black/[0.05] px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-ink/35 dark:bg-white/10 dark:text-ink-dark/40">
          Soon
        </span>
      </div>
    </nav>
  );
}

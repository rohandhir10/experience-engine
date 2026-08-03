import Link from "next/link";

const SOON_ITEMS = ["Adaptations", "Favorites", "Collections", "Usage", "Settings"];
const SOON_ITEMS_LOWER = ["API", "Billing"];

function SoonRow({ label }: { label: string }) {
  return (
    <div className="flex items-center justify-between px-3 py-2 text-[13px] text-ink/30 dark:text-ink-dark/30">
      <span>{label}</span>
      <span className="rounded-full bg-black/[0.05] px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-ink/35 dark:bg-white/10 dark:text-ink-dark/40">
        Soon
      </span>
    </div>
  );
}

/** Every row but Home is inert on purpose — there's no adaptation history,
 * no favorites/collections storage, no usage metering, and no settings to
 * change yet, since there's no account system behind any of it. Shown
 * dimmed with a "Soon" tag rather than hidden, so the eventual shape of
 * the product is visible without pretending any of it works today. */
export function DashboardSidebar() {
  return (
    <nav className="flex w-full flex-col gap-1 sm:w-48 sm:shrink-0">
      <Link
        href="/dashboard"
        className="rounded-lg bg-black/[0.04] px-3 py-2 text-[13px] font-medium text-ink dark:bg-white/[0.06] dark:text-ink-dark"
      >
        Home
      </Link>
      {SOON_ITEMS.map((item) => (
        <SoonRow key={item} label={item} />
      ))}
      <div className="my-2 border-t border-black/[0.05] dark:border-white/[0.05]" />
      {SOON_ITEMS_LOWER.map((item) => (
        <SoonRow key={item} label={item} />
      ))}
    </nav>
  );
}

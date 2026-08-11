import { SiteHeader } from "@/components/SiteHeader";
import { DashboardSidebar } from "@/components/DashboardSidebar";
import { RecentAdaptations } from "@/components/RecentAdaptations";

export const metadata = { title: "CASTIA — Adaptations" };

// No longer a DashboardStub: this was the one dashboard section still
// claiming "there's no sign-in yet" after accounts, favorites, and
// collections were all built for real - same RecentAdaptations
// component the Home page's "Recent Adaptations" section and the
// Favorites page already use (favoritesOnly omitted here shows the
// FULL history, both mediums together, same as Home's).
export default function AdaptationsPage() {
  return (
    <main className="min-h-screen px-6 pb-28 pt-8 sm:px-10">
      <div className="mx-auto max-w-5xl">
        <SiteHeader />

        <div className="mt-10 flex flex-col gap-10 sm:flex-row">
          <DashboardSidebar active="adaptations" />

          <div className="min-w-0 flex-1">
            <h1 className="font-serif text-2xl text-ink dark:text-ink-dark sm:text-[1.75rem]">
              Adaptations
            </h1>
            <p className="mt-2 text-[13px] text-ink/62 dark:text-ink-dark/62">
              Every song and comic chapter you've adapted, most recent
              first — songs and webtoons together.
            </p>
            <RecentAdaptations />
          </div>
        </div>
      </div>
    </main>
  );
}

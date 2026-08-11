import { SiteHeader } from "@/components/SiteHeader";
import { DashboardSidebar } from "@/components/DashboardSidebar";
import { RecentAdaptations } from "@/components/RecentAdaptations";

export const metadata = { title: "CASTIA — Favorites" };

// No longer a DashboardStub: favorites are real now (the star in any
// history list writes through to server/accounts.py::set_favorite).
// Same chrome as the stub pages so the sidebar still feels continuous.
export default function FavoritesPage() {
  return (
    <main className="min-h-screen px-6 pb-28 pt-8 sm:px-10">
      <div className="mx-auto max-w-5xl">
        <SiteHeader />

        <div className="mt-10 flex flex-col gap-10 sm:flex-row">
          <DashboardSidebar active="favorites" />

          <div className="min-w-0 flex-1">
            <h1 className="font-serif text-2xl text-ink dark:text-ink-dark sm:text-[1.75rem]">
              Favorites
            </h1>
            <p className="mt-2 text-[13px] text-ink/62 dark:text-ink-dark/62">
              The adaptations you've starred.
            </p>
            <RecentAdaptations favoritesOnly />
          </div>
        </div>
      </div>
    </main>
  );
}

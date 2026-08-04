import { SiteHeader } from "@/components/SiteHeader";
import { DashboardSidebar } from "@/components/DashboardSidebar";
import { CollectionsManager } from "@/components/CollectionsManager";

export const metadata = { title: "AURA — Collections" };

// No longer a DashboardStub: collections are real (server/accounts.py).
export default function CollectionsPage() {
  return (
    <main className="min-h-screen px-6 pb-28 pt-8 sm:px-10">
      <div className="mx-auto max-w-5xl">
        <SiteHeader />

        <div className="mt-10 flex flex-col gap-10 sm:flex-row">
          <DashboardSidebar active="collections" />

          <div className="min-w-0 flex-1">
            <h1 className="font-serif text-2xl text-ink dark:text-ink-dark sm:text-[1.75rem]">
              Collections
            </h1>
            <p className="mt-2 text-[13px] text-ink/40 dark:text-ink-dark/40">
              Group your adaptations however you like — by artist, language,
              or mood.
            </p>
            <CollectionsManager />
          </div>
        </div>
      </div>
    </main>
  );
}

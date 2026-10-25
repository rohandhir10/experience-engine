import Link from "next/link";
import { SiteHeader } from "@/components/SiteHeader";
import { DashboardSidebar } from "@/components/DashboardSidebar";
import { RecentAdaptations } from "@/components/RecentAdaptations";

export default function DashboardPage() {
  return (
    <main className="min-h-screen px-6 pb-28 pt-8 sm:px-10">
      <div className="mx-auto max-w-5xl">
        <SiteHeader />

        <div data-screenshot="dashboard-workspace" className="mt-10 flex flex-col gap-10 sm:flex-row">
          <DashboardSidebar active="home" />

          <div className="min-w-0 flex-1">
            <div className="rounded-3xl border border-black/[0.10] bg-white/60 p-7 dark:border-white/[0.10] dark:bg-white/[0.03] sm:p-9">
              <p className="text-[11px] font-medium uppercase tracking-[0.2em] text-accent">CASTIA / WEBTOON STUDIO</p>
              <h1 className="mt-4 max-w-xl font-serif text-3xl leading-tight tracking-tight text-ink dark:text-ink-dark sm:text-4xl">
                Every character deserves their own voice.
              </h1>
              <p className="mt-4 max-w-xl text-[15px] leading-7 text-ink/75 dark:text-ink-dark/72">
                Upload a chapter, review extracted speech bubbles, adapt dialogue with scene context, and prepare panels for redraw — all in one workspace.
              </p>
              <div className="mt-7 flex flex-wrap items-center gap-3">
                <Link href="/comics" className="inline-flex items-center gap-2 rounded-full bg-ink px-6 py-3 text-[13px] font-medium text-paper transition hover:opacity-90 active:scale-[0.98] dark:bg-ink-dark dark:text-paper-dark">
                  Open webtoon workspace <span aria-hidden="true">↗</span>
                </Link>
                <Link href="/manga-webtoon-translation" className="rounded-full border border-black/[0.12] px-6 py-3 text-[13px] font-medium text-ink transition hover:border-black/25 dark:border-white/[0.15] dark:text-ink-dark dark:hover:border-white/25">
                  How localization works
                </Link>
              </div>
              <div className="mt-8 grid gap-3 border-t border-black/[0.08] pt-6 dark:border-white/[0.09] sm:grid-cols-3">
                <div><p className="text-[12px] font-medium text-ink dark:text-ink-dark">01 / Extract</p><p className="mt-1 text-[12px] leading-relaxed text-ink/65 dark:text-ink-dark/65">Read dialogue from uploaded panels.</p></div>
                <div><p className="text-[12px] font-medium text-ink dark:text-ink-dark">02 / Adapt</p><p className="mt-1 text-[12px] leading-relaxed text-ink/65 dark:text-ink-dark/65">Keep voice and context in view.</p></div>
                <div><p className="text-[12px] font-medium text-ink dark:text-ink-dark">03 / Review</p><p className="mt-1 text-[12px] leading-relaxed text-ink/65 dark:text-ink-dark/65">Review choices before export.</p></div>
              </div>
            </div>

            <div data-screenshot="dashboard-recent-boundary" className="mt-12 border-t border-black/[0.09] pt-8 dark:border-white/[0.09]">
              <h2 className="text-[12px] font-medium uppercase tracking-[0.14em] text-ink/62 dark:text-ink-dark/62">
                Recent comic adaptations
              </h2>
              <RecentAdaptations medium="webtoons" />
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}

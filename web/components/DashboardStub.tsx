import Link from "next/link";
import { SiteHeader } from "./SiteHeader";
import { DashboardSidebar } from "./DashboardSidebar";

type DashboardSection =
  | "home"
  | "adaptations"
  | "favorites"
  | "collections"
  | "usage"
  | "settings"
  | "billing";

/** Shared shell for every dashboard section that isn't live yet — same
 * header/sidebar chrome as the real Home page, so clicking through the
 * sidebar feels like a real product, but each page says outright why
 * there's nothing here rather than faking content. */
export function DashboardStub({
  active,
  title,
  message,
  secondaryLink,
}: {
  active: DashboardSection;
  title: string;
  message: string;
  secondaryLink?: { href: string; label: string };
}) {
  return (
    <main className="min-h-screen px-6 pb-28 pt-8 sm:px-10">
      <div className="mx-auto max-w-5xl">
        <SiteHeader />

        <div className="mt-10 flex flex-col gap-10 sm:flex-row">
          <DashboardSidebar active={active} />

          <div className="min-w-0 flex-1">
            <h1 className="font-serif text-2xl text-ink dark:text-ink-dark sm:text-[1.75rem]">
              {title}
            </h1>
            <p className="mt-4 max-w-prose text-[14px] leading-relaxed text-ink/45 dark:text-ink-dark/45">
              {message}
            </p>
            <div className="mt-8 flex items-center gap-5">
              <Link
                href="/dashboard"
                className="text-[13px] text-ink/45 underline decoration-ink/15 underline-offset-4 transition hover:text-ink/70 hover:decoration-ink/30 dark:text-ink-dark/45 dark:decoration-ink-dark/15 dark:hover:text-ink-dark/70"
              >
                ← Back to Home
              </Link>
              {secondaryLink && (
                <Link
                  href={secondaryLink.href}
                  className="text-[13px] text-ink/45 underline decoration-ink/15 underline-offset-4 transition hover:text-ink/70 hover:decoration-ink/30 dark:text-ink-dark/45 dark:decoration-ink-dark/15 dark:hover:text-ink-dark/70"
                >
                  {secondaryLink.label} →
                </Link>
              )}
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}

import Link from "next/link";
import { SiteHeader } from "@/components/SiteHeader";
import { Footer } from "@/components/Footer";

export const metadata = {
  title: "Page Not Found",
  robots: { index: false, follow: true },
};

// Next.js's own default 404 (a bare "404 / This page could not be
// found." with no styling, no nav, no way back to the site) rendered
// for every unmatched route until this file existed - a real gap found
// visually auditing the site: every other dead-end state in this
// project (an invalid share link on /s/[id] and /comics/s/[id]) already
// gets a real, on-brand "doesn't lead anywhere" screen with the logo and
// a way forward; a mistyped or stale URL got nothing at all. Mirrors
// that same pattern - SiteHeader/Footer so the visitor never loses the
// site chrome, not a special one-off design.
export default function NotFound() {
  return (
    <main className="min-h-screen px-6 pb-28 pt-8 sm:px-10">
      <div className="mx-auto max-w-5xl">
        <SiteHeader />

        <div className="mx-auto mt-24 flex max-w-md flex-col items-center text-center sm:mt-32">
          <p className="text-[12px] uppercase tracking-[0.15em] text-accent">404</p>
          <h1 className="mt-3 font-serif text-2xl text-ink dark:text-ink-dark sm:text-[1.75rem]">
            This page doesn't exist.
          </h1>
          <p className="mt-3 text-[14px] leading-relaxed text-ink/68 dark:text-ink-dark/68">
            The link may be mistyped, or the page may have moved. Here's how to
            get back to something real.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Link
              href="/"
              className="rounded-full bg-ink px-6 py-3 text-[14px] font-medium text-paper transition active:scale-[0.97] dark:bg-ink-dark dark:text-paper-dark"
            >
              Go home
            </Link>
            <Link
              href="/faq"
              className="text-[13px] text-ink/75 underline decoration-ink/20 underline-offset-4 transition hover:text-ink/78 dark:text-ink-dark/75 dark:decoration-ink-dark/20 dark:hover:text-ink-dark/78"
            >
              See the FAQ
            </Link>
          </div>
        </div>

        <Footer />
      </div>
    </main>
  );
}

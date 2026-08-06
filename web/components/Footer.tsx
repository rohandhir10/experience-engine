import Link from "next/link";

/** Real internal links only - no social icons pointing at accounts that
 * don't exist, no newsletter signup that isn't wired to anything. Placed
 * on marketing/product pages only (not /dashboard/*, /sign-in), since
 * those aren't pages a visitor is trying to navigate away from. `dark`
 * matches the page's own forced-dark shell (e.g. /music, /comics) so the
 * footer doesn't look like a mistake pasted onto a dark page. */
export function Footer({ dark }: { dark?: boolean } = {}) {
  const dim = dark
    ? "text-white/40 hover:text-white/70"
    : "text-ink/40 hover:text-ink/70 dark:text-ink-dark/40 dark:hover:text-ink-dark/70";
  const border = dark ? "border-white/10" : "border-black/[0.06] dark:border-white/[0.07]";

  return (
    <footer className={`mx-auto mt-24 w-full max-w-4xl border-t px-0 pt-8 ${border}`}>
      <nav className="flex flex-wrap items-center gap-x-6 gap-y-2 text-[13px]">
        <Link href="/music" className={`transition ${dim}`}>
          Music
        </Link>
        <Link href="/comics" className={`transition ${dim}`}>
          Webtoons
        </Link>
        <Link href="/lyrics-translation" className={`transition ${dim}`}>
          Lyric translation
        </Link>
        <Link href="/manga-webtoon-translation" className={`transition ${dim}`}>
          Manga &amp; webtoon translation
        </Link>
        <Link href="/how-it-works" className={`transition ${dim}`}>
          How it works
        </Link>
        <Link href="/faq" className={`transition ${dim}`}>
          FAQ
        </Link>
        <Link href="/pricing" className={`transition ${dim}`}>
          Pricing
        </Link>
        <Link href="/blog" className={`transition ${dim}`}>
          Blog
        </Link>
        <Link href="/glossary" className={`transition ${dim}`}>
          Glossary
        </Link>
        <Link href="/dashboard/settings" className={`transition ${dim}`}>
          API
        </Link>
      </nav>
      <nav className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-1.5 text-[12px]">
        <Link href="/terms" className={`transition ${dim}`}>
          Terms
        </Link>
        <Link href="/privacy" className={`transition ${dim}`}>
          Privacy
        </Link>
        <Link href="/refunds" className={`transition ${dim}`}>
          Refunds
        </Link>
        <Link href="/dmca" className={`transition ${dim}`}>
          DMCA
        </Link>
      </nav>
      <p className={`mt-4 text-[12px] ${dark ? "text-white/25" : "text-ink/30 dark:text-ink-dark/30"}`}>
        © {new Date().getFullYear()} Castia
      </p>
    </footer>
  );
}

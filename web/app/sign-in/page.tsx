import Link from "next/link";
import { SiteHeader } from "@/components/SiteHeader";

export const metadata = {
  title: "AURA — Sign In",
  description: "Accounts aren't live yet.",
};

export default function SignInPage() {
  return (
    <main className="min-h-screen px-6 pb-28 pt-8 sm:px-10">
      <div className="mx-auto max-w-3xl">
        <SiteHeader />
      </div>

      <div className="mx-auto mt-24 flex max-w-sm flex-col items-center text-center">
        <h1 className="font-serif text-2xl text-ink dark:text-ink-dark">
          Accounts aren't live yet.
        </h1>
        <p className="mt-3 text-[14px] leading-relaxed text-ink/50 dark:text-ink-dark/50">
          You don't need one to use AURA — every adaptation is free to try
          right now. Sign-in is coming as usage grows.
        </p>

        <button
          disabled
          className="mt-8 inline-flex w-full cursor-not-allowed items-center justify-center gap-3 rounded-full border border-black/10 px-6 py-3 text-[14px] font-medium text-ink/35 dark:border-white/10 dark:text-ink-dark/35"
        >
          Continue with Google
        </button>

        <Link
          href="/#lyrics"
          className="mt-6 text-[13px] text-ink/45 underline decoration-ink/15 underline-offset-4 transition hover:text-ink/70 dark:text-ink-dark/45 dark:decoration-ink-dark/15 dark:hover:text-ink-dark/70"
        >
          Just take me to AURA →
        </Link>
      </div>
    </main>
  );
}

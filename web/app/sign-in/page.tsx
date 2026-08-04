import Link from "next/link";
import { SiteHeader } from "@/components/SiteHeader";
import { auth, signIn, signOut } from "@/auth";

export const metadata = {
  title: "CASTIA — Sign In",
  description: "Sign in with Google to keep your adaptation history.",
};

// Server component: session comes from the Auth.js JWT cookie and the
// buttons are server actions - no client-side auth state to hydrate.
// Google is deliberately the only provider (the stated auth plan). On a
// deployment without the auth env vars this renders the honest
// "not live yet" state instead of a button that breaks at click time.
export default async function SignInPage() {
  const session = await auth().catch(() => null);
  const configured = Boolean(process.env.AUTH_GOOGLE_ID && process.env.AUTH_SECRET);

  return (
    <main className="min-h-screen px-6 pb-28 pt-8 sm:px-10">
      <div className="mx-auto max-w-3xl">
        <SiteHeader />
      </div>

      <div className="mx-auto mt-24 flex max-w-sm flex-col items-center text-center">
        {session?.user ? (
          <>
            <h1 className="font-serif text-2xl text-ink dark:text-ink-dark">
              You're signed in.
            </h1>
            <p className="mt-3 text-[14px] leading-relaxed text-ink/50 dark:text-ink-dark/50">
              {session.user.email} — your adaptations are saved to your
              history.
            </p>
            <Link
              href="/dashboard"
              className="mt-8 inline-flex w-full items-center justify-center rounded-full bg-ink px-6 py-3 text-[14px] font-medium text-paper transition active:scale-[0.97] dark:bg-ink-dark dark:text-paper-dark"
            >
              Go to your dashboard
            </Link>
            <form
              action={async () => {
                "use server";
                await signOut({ redirectTo: "/" });
              }}
              className="mt-4 w-full"
            >
              <button
                type="submit"
                className="w-full rounded-full border border-black/10 px-6 py-3 text-[14px] text-ink/60 transition hover:text-ink dark:border-white/10 dark:text-ink-dark/60 dark:hover:text-ink-dark"
              >
                Sign out
              </button>
            </form>
          </>
        ) : configured ? (
          <>
            <h1 className="font-serif text-2xl text-ink dark:text-ink-dark">
              Keep your adaptations.
            </h1>
            <p className="mt-3 text-[14px] leading-relaxed text-ink/50 dark:text-ink-dark/50">
              You don't need an account to use CASTIA — sign in to keep a
              history of every song you adapt, on any device.
            </p>
            <form
              action={async () => {
                "use server";
                await signIn("google", { redirectTo: "/dashboard" });
              }}
              className="mt-8 w-full"
            >
              <button
                type="submit"
                className="inline-flex w-full items-center justify-center gap-3 rounded-full bg-ink px-6 py-3 text-[14px] font-medium text-paper transition active:scale-[0.97] dark:bg-ink-dark dark:text-paper-dark"
              >
                Continue with Google
              </button>
            </form>
          </>
        ) : (
          <>
            <h1 className="font-serif text-2xl text-ink dark:text-ink-dark">
              Accounts aren't live yet.
            </h1>
            <p className="mt-3 text-[14px] leading-relaxed text-ink/50 dark:text-ink-dark/50">
              You don't need one to use CASTIA — every adaptation is free to
              try right now. (Deployment note: set AUTH_SECRET,
              AUTH_GOOGLE_ID and AUTH_GOOGLE_SECRET to enable sign-in.)
            </p>
          </>
        )}

        <Link
          href="/music#lyrics"
          className="mt-6 text-[13px] text-ink/45 underline decoration-ink/15 underline-offset-4 transition hover:text-ink/70 dark:text-ink-dark/45 dark:decoration-ink-dark/15 dark:hover:text-ink-dark/70"
        >
          Just take me to CASTIA →
        </Link>
      </div>
    </main>
  );
}

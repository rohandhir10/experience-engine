import Link from "next/link";
import { redirect } from "next/navigation";
import { SiteHeader } from "@/components/SiteHeader";
import { auth, signIn, signOut } from "@/auth";
import { AuthError } from "next-auth";

export const metadata = {
  title: "Sign In",
  description: "Sign in with Google or your email to keep your adaptation history.",
  robots: { index: false, follow: true },
};

const ERROR_MESSAGES: Record<string, string> = {
  email_not_verified: "Verify your email first - check your inbox for the link, or resend it from the sign-up page.",
  default: "Wrong email or password.",
};

// Server component: session comes from the Auth.js JWT cookie. Google
// sign-in is a server action (unchanged); email/password is a second
// server action calling signIn("credentials", ...) - both funnel into
// the same session. A failed credentials sign-in redirects back here
// with ?error=CredentialsSignin&code=<code> (set in web/auth.ts's
// EmailNotVerifiedError, or next-auth's own default for anything else),
// which searchParams below turns into a real message instead of a
// generic "something went wrong."
export default async function SignInPage({
  searchParams,
}: {
  searchParams: { error?: string; code?: string };
}) {
  const session = await auth().catch(() => null);
  const configured = Boolean(process.env.AUTH_SECRET);
  const googleConfigured = Boolean(process.env.AUTH_GOOGLE_ID);
  const errorMessage = searchParams.error
    ? ERROR_MESSAGES[searchParams.code ?? ""] ?? ERROR_MESSAGES.default
    : null;

  async function credentialsSignIn(formData: FormData) {
    "use server";
    try {
      await signIn("credentials", {
        email: formData.get("email"),
        password: formData.get("password"),
        redirectTo: "/dashboard",
      });
    } catch (error) {
      if (error instanceof AuthError) {
        const code = "code" in error ? String((error as { code?: string }).code ?? "") : "";
        redirect(`/sign-in?error=${error.type}&code=${code}`);
      }
      throw error;
    }
  }

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
            <p className="mt-3 text-[14px] leading-relaxed text-ink/68 dark:text-ink-dark/68">
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
                className="w-full rounded-full border border-black/10 px-6 py-3 text-[14px] text-ink/72 transition hover:text-ink dark:border-white/10 dark:text-ink-dark/72 dark:hover:text-ink-dark"
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
            <p className="mt-3 text-[14px] leading-relaxed text-ink/68 dark:text-ink-dark/68">
              You don't need an account to use CASTIA — sign in to keep a
              history of every song you adapt, on any device.
            </p>

            {errorMessage && (
              <p className="mt-6 text-[13px] text-red-600/80 dark:text-red-400/80">{errorMessage}</p>
            )}

            {googleConfigured && (
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
            )}

            <div className="mt-6 flex w-full items-center gap-3 text-[12px] text-ink/65 dark:text-ink-dark/65">
              <div className="h-px flex-1 bg-black/[0.08] dark:bg-white/[0.08]" />
              or
              <div className="h-px flex-1 bg-black/[0.08] dark:bg-white/[0.08]" />
            </div>

            <form action={credentialsSignIn} className="mt-6 w-full space-y-3 text-left">
              <div>
                <label htmlFor="email" className="text-[12px] text-ink/75 dark:text-ink-dark/75">
                  Email
                </label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  required
                  autoComplete="email"
                  className="mt-1 w-full rounded-lg border border-black/10 bg-transparent px-3.5 py-2.5 text-[14px] text-ink outline-none focus:border-ink/30 dark:border-white/10 dark:text-ink-dark dark:focus:border-ink-dark/30"
                />
              </div>
              <div>
                <label htmlFor="password" className="text-[12px] text-ink/75 dark:text-ink-dark/75">
                  Password
                </label>
                <input
                  id="password"
                  name="password"
                  type="password"
                  required
                  autoComplete="current-password"
                  className="mt-1 w-full rounded-lg border border-black/10 bg-transparent px-3.5 py-2.5 text-[14px] text-ink outline-none focus:border-ink/30 dark:border-white/10 dark:text-ink-dark dark:focus:border-ink-dark/30"
                />
              </div>
              <button
                type="submit"
                className="w-full rounded-full border border-black/10 px-6 py-3 text-[14px] font-medium text-ink transition hover:border-ink/30 dark:border-white/10 dark:text-ink-dark dark:hover:border-ink-dark/30"
              >
                Sign in with email
              </button>
            </form>

            <p className="mt-6 text-[13px] text-ink/75 dark:text-ink-dark/75">
              No account?{" "}
              <Link href="/sign-up" className="underline decoration-ink/20 underline-offset-4">
                Sign up
              </Link>
            </p>
          </>
        ) : (
          <>
            <h1 className="font-serif text-2xl text-ink dark:text-ink-dark">
              Accounts aren't live yet.
            </h1>
            <p className="mt-3 text-[14px] leading-relaxed text-ink/68 dark:text-ink-dark/68">
              You don't need one to use CASTIA — every adaptation is free to
              try right now. (Deployment note: set AUTH_SECRET and
              CASTIA_INTERNAL_API_SECRET to enable email sign-in; add
              AUTH_GOOGLE_ID/AUTH_GOOGLE_SECRET for Google too.)
            </p>
          </>
        )}

        <Link
          href="/music#lyrics"
          className="mt-6 text-[13px] text-ink/75 underline decoration-ink/15 underline-offset-4 transition hover:text-ink/78 dark:text-ink-dark/75 dark:decoration-ink-dark/15 dark:hover:text-ink-dark/78"
        >
          Just take me to CASTIA →
        </Link>
      </div>
    </main>
  );
}

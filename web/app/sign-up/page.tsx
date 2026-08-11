import Link from "next/link";
import { SiteHeader } from "@/components/SiteHeader";
import { signIn } from "@/auth";
import { SignUpForm } from "./SignUpForm";

export const metadata = {
  title: "Sign Up",
  description: "Create a CASTIA account to keep a history of every adaptation, on any device.",
  robots: { index: false, follow: true },
};

// A server component (unlike the old single-file client component this
// replaced) specifically so it can read process.env.AUTH_GOOGLE_ID and
// define the "use server" signIn("google") action /sign-in already has -
// neither is available inside a "use client" file. The actual form UI
// (email/password state, submit/resend handling) still lives in the
// client-only SignUpForm below it; this file only owns what genuinely
// needs the server.
export default async function SignUpPage() {
  const googleConfigured = Boolean(process.env.AUTH_GOOGLE_ID);

  async function googleSignUp() {
    "use server";
    await signIn("google", { redirectTo: "/dashboard" });
  }

  return (
    <main className="min-h-screen px-6 pb-28 pt-8 sm:px-10">
      <div className="mx-auto max-w-3xl">
        <SiteHeader />
      </div>

      <div className="mx-auto mt-24 flex max-w-sm flex-col items-center text-center">
        <SignUpForm
          googleConfigured={googleConfigured}
          googleSignUp={googleConfigured ? googleSignUp : undefined}
        />

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

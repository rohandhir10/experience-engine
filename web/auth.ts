import NextAuth, { CredentialsSignin } from "next-auth";
import Google from "next-auth/providers/google";
import Credentials from "next-auth/providers/credentials";
import { ENGINE_API_URL } from "@/lib/api";

// Auth.js (NextAuth v5), JWT session strategy - deliberately NO database
// adapter. The Python API (server/accounts.py, server/password_auth.py)
// is the single owner of user rows; giving Auth.js its own
// users/accounts/sessions tables would duplicate that store in the exact
// way server/db.py's docstring warned about. The JWT cookie carries the
// only session state that exists, and our own user id rides inside it
// (castiaUserId below).
//
// Two providers now: Google (OAuth, email already verified by Google) and
// Credentials (email/password, server/password_auth.py - needs its own
// verification step since nothing here vouches for the address the way
// Google does). Both funnel into the same `users` table and the same
// jwt callback below.
//
// Required env vars (Vercel project settings):
//   AUTH_SECRET          - `npx auth secret` or any long random string
//   AUTH_GOOGLE_ID       - Google OAuth client id
//   AUTH_GOOGLE_SECRET   - Google OAuth client secret
//   CASTIA_INTERNAL_API_SECRET - same value as on the Railway service;
//                          proves sync/login/register calls come from
//                          this server, not a browser (see server/main.py).

declare module "next-auth" {
  interface Session {
    castiaUserId?: string;
    plan?: string;
  }
}

// A distinct, stable `code` so the sign-in page (searchParams.code) can
// tell "right password, email just isn't verified yet" apart from every
// other failure (wrong password, no such account) without parsing a
// message string - see next-auth's CredentialsSignin docs on `code`
// becoming `?error=CredentialsSignin&code=<code>` on the redirect back.
class EmailNotVerifiedError extends CredentialsSignin {
  code = "email_not_verified";
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Google,
    Credentials({
      credentials: {
        email: { label: "Email" },
        password: { label: "Password", type: "password" },
      },
      // Runs server-side only (this is the Next.js server, never the
      // browser) - the one place it's safe to hold CASTIA_INTERNAL_API_SECRET
      // and call server/main.py's /api/auth/login directly with a plaintext
      // password over the (internal, HTTPS) service-to-service hop.
      async authorize(credentials) {
        const email = typeof credentials?.email === "string" ? credentials.email : "";
        const password = typeof credentials?.password === "string" ? credentials.password : "";
        if (!email || !password) return null;

        let body: { status: string; id?: string; email?: string; plan?: string };
        try {
          const res = await fetch(`${ENGINE_API_URL}/api/auth/login`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-Castia-Internal-Secret": process.env.CASTIA_INTERNAL_API_SECRET ?? "",
            },
            body: JSON.stringify({ email, password }),
          });
          if (!res.ok) return null;
          body = await res.json();
        } catch {
          return null;
        }

        if (body.status === "unverified") throw new EmailNotVerifiedError();
        if (body.status !== "ok" || !body.id) return null;
        // /api/auth/login already resolved the account (id, plan) - no
        // second round-trip to /api/users/sync needed, unlike Google's
        // branch below, which only has a fresh OAuth profile to work with.
        return { id: body.id, email: body.email, plan: body.plan };
      },
    }),
  ],
  session: { strategy: "jwt" },
  pages: { signIn: "/sign-in" },
  callbacks: {
    async jwt({ token, account, profile, user }) {
      // First sign-in only (account is present just once): upsert the
      // user on the Python side and stash OUR id in the token. If the
      // sync fails, the user is still signed in - history simply won't
      // record until a future sign-in succeeds. Degrade, don't block.
      if (account?.provider === "google" && profile?.sub) {
        try {
          const res = await fetch(`${ENGINE_API_URL}/api/users/sync`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-Castia-Internal-Secret": process.env.CASTIA_INTERNAL_API_SECRET ?? "",
            },
            body: JSON.stringify({
              google_sub: profile.sub,
              email: profile.email ?? null,
              display_name: profile.name ?? null,
            }),
          });
          if (res.ok) {
            const synced = await res.json();
            token.castiaUserId = synced.id;
            token.plan = synced.plan;
          } else {
            console.error(`user sync failed: ${res.status}`);
          }
        } catch (err) {
          console.error("user sync unreachable", err);
        }
      } else if (account?.provider === "credentials" && user) {
        // authorize() above already did the one round-trip this needs.
        token.castiaUserId = user.id;
        if (typeof (user as { plan?: string }).plan === "string") {
          token.plan = (user as { plan?: string }).plan;
        }
      }
      return token;
    },
    async session({ session, token }) {
      if (typeof token.castiaUserId === "string") session.castiaUserId = token.castiaUserId;
      if (typeof token.plan === "string") session.plan = token.plan;
      return session;
    },
  },
});

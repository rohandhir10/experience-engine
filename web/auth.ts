import NextAuth from "next-auth";
import Google from "next-auth/providers/google";
import { ENGINE_API_URL } from "@/lib/api";

// Auth.js (NextAuth v5), Google-only, JWT session strategy - deliberately
// NO database adapter. The Python API (server/accounts.py) is the single
// owner of user rows; giving Auth.js its own users/accounts/sessions
// tables would duplicate that store in the exact way server/db.py's
// docstring warned about. The JWT cookie carries the only session state
// that exists, and our own user id rides inside it (auraUserId below).
//
// Required env vars (Vercel project settings):
//   AUTH_SECRET          - `npx auth secret` or any long random string
//   AUTH_GOOGLE_ID       - Google OAuth client id
//   AUTH_GOOGLE_SECRET   - Google OAuth client secret
//   AURA_INTERNAL_API_SECRET - same value as on the Railway service;
//                          proves sync/history calls come from this
//                          server, not a browser (see server/main.py).

declare module "next-auth" {
  interface Session {
    auraUserId?: string;
    plan?: string;
  }
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [Google],
  session: { strategy: "jwt" },
  pages: { signIn: "/sign-in" },
  callbacks: {
    async jwt({ token, account, profile }) {
      // First sign-in only (account is present just once): upsert the
      // user on the Python side and stash OUR id in the token. If the
      // sync fails, the user is still signed in - history simply won't
      // record until a future sign-in succeeds. Degrade, don't block.
      if (account && profile?.sub) {
        try {
          const res = await fetch(`${ENGINE_API_URL}/api/users/sync`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "X-Aura-Internal-Secret": process.env.AURA_INTERNAL_API_SECRET ?? "",
            },
            body: JSON.stringify({
              google_sub: profile.sub,
              email: profile.email ?? null,
              display_name: profile.name ?? null,
            }),
          });
          if (res.ok) {
            const user = await res.json();
            token.auraUserId = user.id;
            token.plan = user.plan;
          } else {
            console.error(`user sync failed: ${res.status}`);
          }
        } catch (err) {
          console.error("user sync unreachable", err);
        }
      }
      return token;
    },
    async session({ session, token }) {
      if (typeof token.auraUserId === "string") session.auraUserId = token.auraUserId;
      if (typeof token.plan === "string") session.plan = token.plan;
      return session;
    },
  },
});

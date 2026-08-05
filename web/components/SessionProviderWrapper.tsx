"use client";

import { SessionProvider } from "next-auth/react";

/** Auth.js's useSession() hook needs a SessionProvider somewhere above
 * it in the tree - nothing needed one until the Paddle checkout button
 * (components/BuyButton.tsx) needed the signed-in user's id client-side
 * (Paddle.js opens checkout in the browser, so the id has to be there
 * too, not just on the server - see that component's doc comment).
 * Every /api/me/* route already reads the session server-side
 * (lib/engineFetch.ts's auth() call) and didn't need this; this is
 * additive, not a replacement for that. */
export function SessionProviderWrapper({ children }: { children: React.ReactNode }) {
  return <SessionProvider>{children}</SessionProvider>;
}

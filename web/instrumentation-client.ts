// Browser runtime. Next.js loads this file automatically on the client
// (the successor to sentry.client.config.ts, which stops working under
// Turbopack).
import * as Sentry from "@sentry/nextjs";
import { SENTRY_DSN, sharedSentryOptions } from "@/lib/sentryOptions";

if (SENTRY_DSN) {
  Sentry.init({
    ...sharedSentryOptions,
    // NO Session Replay. This is the single most important line in the
    // frontend Sentry setup: Replay records the DOM as the user
    // interacts, which on /music and /comics means recording someone
    // typing or pasting the copyrighted lyrics and dialogue they came
    // here to work on, and shipping that video-like recording to a third
    // party. Sentry's own setup wizard adds it by default. It is left
    // out here deliberately, and `integrations` is an explicit empty
    // override rather than an omission so that adding it back has to be
    // a deliberate edit to this line.
    integrations: [],
  });
}

// Lets Sentry tie an error to the navigation that led to it. Exported
// from here because Next only wires this hook up from the client
// instrumentation file.
export const onRouterTransitionStart = Sentry.captureRouterTransitionStart;

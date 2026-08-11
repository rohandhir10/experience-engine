// Edge runtime (middleware.ts, which sets the CSP on every request).
import * as Sentry from "@sentry/nextjs";
import { SENTRY_DSN, sharedSentryOptions } from "@/lib/sentryOptions";

if (SENTRY_DSN) {
  Sentry.init(sharedSentryOptions);
}

import type { Breadcrumb, ErrorEvent } from "@sentry/nextjs";

/** Shared Sentry options for all three Next.js runtimes (browser, Node
 * server, edge middleware).
 *
 * Kept in one place because the privacy locks below are the whole point,
 * and three near-identical config files are exactly how one of them
 * quietly ends up different from the others.
 *
 * Everything here mirrors the reasoning already written down in
 * server/monitoring.py for the Python side - same product, same content,
 * same obligations - with one addition that only exists in a browser:
 * Session Replay. See `disabled integrations` below.
 */

/** Empty string when unset, which @sentry/nextjs treats as "do nothing" -
 * so no DSN means no SDK activity, exactly like the Python side.
 *
 * NEXT_PUBLIC_ because the browser bundle needs it at build time. A
 * client-side Sentry DSN is public by design (it is an ingest key, not a
 * credential - it can only write events, never read them), which is why
 * this is a different variable from the server's CASTIA_SENTRY_DSN and
 * should be a different Sentry project key.
 */
export const SENTRY_DSN = process.env.NEXT_PUBLIC_SENTRY_DSN || "";

/** Scrubs anything credential-shaped before an event leaves the browser
 * or the server runtime. Mirrors server/monitoring.py::scrub_event. */
export function scrubEvent(event: ErrorEvent): ErrorEvent {
  const request = event.request;
  if (request && typeof request === "object") {
    // The request body of an adapt/OCR call IS the user's lyrics or a
    // chapter's dialogue. Never send it.
    delete request.data;
    delete request.cookies;

    const headers = request.headers as Record<string, string> | undefined;
    if (headers && typeof headers === "object") {
      for (const key of Object.keys(headers)) {
        if (/authorization|cookie|secret|token|api[-_]?key/i.test(key)) {
          headers[key] = "[redacted]";
        }
      }
    }
  }
  return event;
}

export const sharedSentryOptions = {
  dsn: SENTRY_DSN,
  environment: process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT || "production",

  // --- privacy locks, same reasoning as server/monitoring.py ---
  // Never attach IP addresses, cookies or user identifiers automatically.
  sendDefaultPii: false,
  // Performance tracing is a separate cost and a larger data-collection
  // question; off until somebody decides they want it.
  tracesSampleRate: 0,
  beforeSend: scrubEvent,

  // Breadcrumbs are the browser-side equivalent of the request-body
  // problem: by default Sentry records console output and every fetch,
  // and this app's fetches carry lyrics and panel text. Only the
  // navigation trail is worth keeping, and only it is kept.
  beforeBreadcrumb(breadcrumb: Breadcrumb): Breadcrumb | null {
    if (breadcrumb.category === "navigation" || breadcrumb.category === "ui.click") {
      return breadcrumb;
    }
    // Drops console, fetch and xhr breadcrumbs outright.
    return null;
  },
};

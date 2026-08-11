"use client";

import { useEffect } from "react";
import * as Sentry from "@sentry/nextjs";

/** The last-resort boundary: a React rendering error thrown high enough
 * to take out the root layout. Next replaces the entire document with
 * this, which is why it has to render its own <html>/<body> and can't
 * use the app's shared layout, header or fonts.
 *
 * Two jobs. It reports the error - without this file these are the one
 * class of failure Sentry never sees, because nothing else in the tree
 * survives to catch them (the build warns about exactly this). And it
 * gives the user something other than a blank white page: styles are
 * inline because whatever just failed may have taken the stylesheet's
 * layout with it, and a "recovery" screen that itself renders unstyled
 * is not much of a recovery.
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontFamily:
            "ui-sans-serif, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
          background: "#faf9f7",
          color: "#1a1a1a",
          padding: "2rem",
        }}
      >
        <div style={{ maxWidth: "28rem", textAlign: "center" }}>
          <p
            style={{
              fontSize: "12px",
              letterSpacing: "0.15em",
              textTransform: "uppercase",
              opacity: 0.4,
              margin: 0,
            }}
          >
            Castia
          </p>
          <h1 style={{ fontSize: "1.5rem", fontWeight: 500, margin: "0.75rem 0 0" }}>
            Something went wrong.
          </h1>
          <p style={{ fontSize: "14px", lineHeight: 1.6, opacity: 0.6, marginTop: "0.75rem" }}>
            This page hit an unexpected error. It has been reported automatically —
            no adaptation you&apos;ve already run is affected.
          </p>
          <div
            style={{
              marginTop: "1.5rem",
              display: "flex",
              gap: "0.75rem",
              justifyContent: "center",
            }}
          >
            <button
              type="button"
              onClick={() => reset()}
              style={{
                borderRadius: "9999px",
                border: "none",
                background: "#1a1a1a",
                color: "#faf9f7",
                padding: "0.5rem 1.25rem",
                fontSize: "13px",
                fontWeight: 500,
                cursor: "pointer",
              }}
            >
              Try again
            </button>
            <a
              href="/"
              style={{
                borderRadius: "9999px",
                border: "1px solid rgba(0,0,0,0.12)",
                padding: "0.5rem 1.25rem",
                fontSize: "13px",
                fontWeight: 500,
                color: "inherit",
                textDecoration: "none",
              }}
            >
              Go home
            </a>
          </div>
          {/* Next's own error id. The one thing that lets support tie a
              user's report to the captured event. */}
          {error.digest && (
            <p style={{ fontSize: "11px", opacity: 0.35, marginTop: "1.5rem" }}>
              Reference: {error.digest}
            </p>
          )}
        </div>
      </body>
    </html>
  );
}

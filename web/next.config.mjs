import { withSentryConfig } from "@sentry/nextjs";

/** @type {import('next').NextConfig} */
const nextConfig = {};

// Wrapping is a no-op for the runtime SDK when no DSN is configured (the
// three sentry.*.config.ts files each check for one before calling
// init), so a deployment without Sentry behaves exactly as before.
export default withSentryConfig(nextConfig, {
  // Source map upload. Without SENTRY_AUTH_TOKEN this step is skipped
  // and the build still succeeds - stack traces just stay minified,
  // which is a worse debugging experience, not a broken build.
  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT,
  authToken: process.env.SENTRY_AUTH_TOKEN,

  // Keeps the build log readable in CI; real errors still surface.
  silent: !process.env.CI,

  // Uploads the maps, then deletes them from the deployed output so the
  // application's source isn't publicly downloadable from the site
  // itself - Sentry can still symbolicate because it has its own copy.
  sourcemaps: { deleteSourcemapsAfterUpload: true },

  // Routes browser events through this app's own domain instead of
  // sentry.io directly. Two reasons, both real here: ad blockers block
  // requests to sentry.io outright (silently losing exactly the error
  // reports from the users most likely to be hitting problems), and it
  // means middleware.ts's connect-src doesn't need a third-party host
  // punched into it for the browser SDK to work at all.
  tunnelRoute: "/monitoring",

  // This project's middleware sets a strict CSP with no 'unsafe-inline'.
  // Sentry's client bundle is injected as a normal Next script, so it is
  // covered by the existing nonce + 'strict-dynamic'; nothing extra is
  // needed for script-src, and the tunnel above keeps connect-src at
  // 'self'. Documented here because "why does the CSP still work" is the
  // first question anyone will have when reading this file.
  //
  // Strips the SDK's own debug logging from the production bundle.
  webpack: { treeshake: { removeDebugLogging: true } },
});

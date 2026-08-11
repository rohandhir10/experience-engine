// Next.js calls register() once per server runtime at startup. The two
// server-side Sentry configs are loaded here rather than imported at
// module scope anywhere, which is what keeps the Node-only SDK out of
// the edge bundle and vice versa.
export async function register() {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    await import("./sentry.server.config");
  }
  if (process.env.NEXT_RUNTIME === "edge") {
    await import("./sentry.edge.config");
  }
}

// Surfaces errors thrown inside React Server Components / route handlers
// that Next would otherwise only log to its own console.
export { captureRequestError as onRequestError } from "@sentry/nextjs";

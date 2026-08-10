import type { NextRequest } from "next/server";

/** The real end user's IP address, for the engine's per-IP quota
 * (server/quota.py), pulled off whatever the hosting platform's edge
 * proxy set on the way in.
 *
 * This has to be forwarded explicitly on every proxied call, because a
 * route handler here talks to the engine over its OWN outbound fetch -
 * so from server/main.py's point of view the peer address is this
 * Next.js server for every visitor on the site. Without this, per-IP
 * quota buckets all of them together: the first few adaptations of the
 * day exhaust the shared bucket and everyone else is refused.
 *
 * Returns null rather than a placeholder when no address is available
 * (a local `next dev` request over loopback often has neither header) -
 * the caller then simply omits the header, and server/main.py falls
 * back to its own peer-address behavior instead of bucketing an entire
 * deployment under a literal "unknown" string.
 */
export function realClientIp(request: NextRequest): string | null {
  // x-forwarded-for is a comma-separated chain, client first, appended to
  // by each proxy in turn - Vercel and Railway both set it. The first
  // entry is the original client; later entries are intermediaries.
  const forwarded = request.headers.get("x-forwarded-for");
  if (forwarded) {
    const first = forwarded.split(",")[0]?.trim();
    if (first) return first;
  }
  // Single-value fallback set by some proxies (nginx's real_ip module,
  // and Vercel alongside x-forwarded-for).
  const real = request.headers.get("x-real-ip")?.trim();
  return real || null;
}

/** The header pair the engine needs to trust a forwarded client address:
 * the address itself, plus the internal secret that proves this came
 * from the Next.js server rather than from anyone on the internet
 * setting a header by hand (see server/main.py::_client_ip).
 *
 * Returns an empty object when the secret isn't configured - without it
 * the engine would ignore the address anyway, so sending it would be
 * noise, and every proxy route here already treats a missing secret as
 * "proceed without forwarded identity" rather than as an error.
 */
export function clientIpHeaders(request: NextRequest): Record<string, string> {
  const secret = process.env.CASTIA_INTERNAL_API_SECRET;
  if (!secret) return {};
  const ip = realClientIp(request);
  if (!ip) return {};
  return {
    "X-Castia-Internal-Secret": secret,
    "X-Castia-Client-IP": ip,
  };
}

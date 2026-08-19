import { NextRequest, NextResponse } from "next/server";

// Real CSP built from an actual audit of this app's client-side code
// (external domains, inline scripts, image sources), not copy-pasted
// boilerplate.
//
// Nonce-based, not hash-based: confirmed by hand (built, served, and
// inspected the actual browser console) that Next.js's App Router emits
// several inline <script>self.__next_f.push(...)</script> tags per page
// carrying streamed React Server Component data - their content differs
// per page and per request, so no fixed set of content hashes could ever
// cover them. A nonce is the only mechanism that actually works with
// this rendering model: Next.js detects the nonce in this middleware's
// CSP header and automatically applies the same value to every script
// tag it renders, not just the one explicit inline script this app adds
// itself (app/layout.tsx's theme-init).
//
// The real, accepted cost: reading a per-request value (the nonce, via
// next/headers in app/layout.tsx) is a Next.js "Dynamic API" - using one
// anywhere in the render tree opts the whole route into dynamic
// (per-request) rendering. Since app/layout.tsx wraps every page, this
// takes every page here from statically prerendered to dynamically
// server-rendered. That's a real, deliberate tradeoff (see the build
// output before/after this change - every route flips from ○ to ƒ), not
// an accident: 'unsafe-inline' would have kept static rendering but
// given away the one protection a CSP actually exists to provide against
// injected/XSS script execution, which isn't an acceptable trade for a
// product with real user accounts, OAuth, and eventual real payments.
export function proxy(request: NextRequest) {
  const nonce = Buffer.from(crypto.randomUUID()).toString("base64");

  const csp = `
    default-src 'self';
    script-src 'self' 'nonce-${nonce}' 'strict-dynamic' https://www.youtube.com https://cdn.paddle.com;
    style-src 'self' 'unsafe-inline';
    img-src 'self' data: blob:;
    font-src 'self';
    connect-src 'self' https://api.paddle.com https://sandbox-api.paddle.com https://checkout-service.paddle.com https://event-tracking.paddle.com;
    frame-src https://www.youtube.com https://www.youtube-nocookie.com https://buy.paddle.com https://sandbox-buy.paddle.com;
    object-src 'none';
    base-uri 'self';
    form-action 'self';
    frame-ancestors 'self';
    upgrade-insecure-requests;
  `
    .replace(/\s{2,}/g, " ")
    .trim();
  // script-src reasoning, source by source:
  //  - 'nonce-...' + 'strict-dynamic': covers every script Next.js
  //    renders (its own framework/RSC-payload scripts, automatically -
  //    see above - plus the explicit theme-init script, which reads the
  //    same nonce via next/headers). 'strict-dynamic' also means a
  //    nonce'd/trusted script is allowed to insert further scripts
  //    regardless of host, which is what lets YoutubeSyncPlayer.tsx's
  //    dynamically-inserted <script src="youtube.com/iframe_api"> load;
  //    per the CSP spec, browsers that support 'strict-dynamic' ignore
  //    host-source entries like 'self' and the explicit youtube.com/
  //    cdn.paddle.com entries below - those exist purely as the
  //    documented fallback for the small minority of browsers that don't
  //    support 'strict-dynamic' yet, where the host-list still applies.
  //  - components/JsonLd.tsx's inline <script type="application/ld+json">
  //    tags need no allowance at all - CSP's script-src only governs
  //    executable script types, and application/ld+json isn't one.
  //  - cdn.paddle.com: Paddle.js's own required script host
  //    (lib/paddle.ts). Unverified against a real transaction - see the
  //    frame/connect-src note below, same caveat applies here.
  //
  // img-src needs both data: and blob:, not just one: comics panel
  // previews use URL.createObjectURL(file) (app/comics/page.tsx) → blob:,
  // and the redraw result image is a data: URL (also app/comics/page.tsx).
  // No external image host is used anywhere in the app (confirmed: no
  // next/image remotePatterns configured, no Google avatar images
  // rendered), so 'self' plus those two schemes is the complete list, not
  // a cautious over-grant.
  //
  // connect-src and frame-src's Paddle domains (api/checkout-service/
  // event-tracking/buy.paddle.com) are the standard, publicly documented
  // ones for Paddle Billing checkout, but this deployment has never run a
  // real Paddle transaction (NEXT_PUBLIC_PADDLE_CLIENT_TOKEN is unset -
  // see lib/paddle.ts, BuyButton.tsx, which both degrade to a clear
  // "not live yet" message without it). Recheck the browser console for
  // CSP violation errors the first time checkout is exercised for real
  // before trusting this list is complete - it hasn't been production-
  // verified end to end.

  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", nonce);
  requestHeaders.set("Content-Security-Policy", csp);

  const response = NextResponse.next({ request: { headers: requestHeaders } });
  response.headers.set("Content-Security-Policy", csp);
  // Defense-in-depth headers CSP's frame-ancestors doesn't fully replace
  // for older browsers, and that weren't set anywhere in this app before.
  response.headers.set("X-Content-Type-Options", "nosniff");
  response.headers.set("X-Frame-Options", "SAMEORIGIN");
  response.headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
  response.headers.set("Permissions-Policy", "camera=(), microphone=(), geolocation=()");

  return response;
}

export const config = {
  matcher: [
    // Every route except static assets and Next's own image optimizer,
    // which don't render HTML and don't need a CSP/nonce header.
    "/((?!_next/static|_next/image|favicon.ico).*)",
  ],
};

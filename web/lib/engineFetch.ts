import { NextResponse } from "next/server";
import { auth } from "@/auth";
import { ENGINE_API_URL } from "./api";

async function forward(
  path: string,
  init: { method?: string; body?: unknown },
  extraHeaders: Record<string, string>
): Promise<NextResponse> {
  const secret = process.env.CASTIA_INTERNAL_API_SECRET;
  if (!secret) {
    return NextResponse.json(
      { error: "Accounts are not configured on this deployment." },
      { status: 503 }
    );
  }

  let upstream: Response;
  try {
    upstream = await fetch(`${ENGINE_API_URL}${path}`, {
      method: init.method ?? "GET",
      headers: {
        "Content-Type": "application/json",
        "X-Castia-Internal-Secret": secret,
        ...extraHeaders,
      },
      ...(init.body === undefined ? {} : { body: JSON.stringify(init.body) }),
      cache: "no-store",
    });
  } catch {
    return NextResponse.json(
      { error: "CASTIA is temporarily unreachable. Please try again in a few minutes." },
      { status: 502 }
    );
  }

  const data = await upstream.json().catch(() => ({}));
  return NextResponse.json(data, { status: upstream.status });
}

/** Server-only helper for the /api/me/* proxy routes, which all share the
 * same shape: read the Auth.js session, refuse if signed out, attach the
 * internal secret + user id, forward to the engine, pass its response
 * through. Extracted once the third route needed it verbatim.
 *
 * The secret is what makes the engine trust the forwarded user id (see
 * server/main.py::_authed_user_id) — it must never reach the browser, so
 * this file is only ever imported from route handlers. */
export async function engineFetchAsUser(
  path: string,
  init?: { method?: string; body?: unknown }
): Promise<NextResponse> {
  const session = await auth().catch(() => null);
  if (!session?.castiaUserId) {
    return NextResponse.json({ error: "Sign in first." }, { status: 401 });
  }
  return forward(path, init ?? {}, { "X-Castia-User-Id": session.castiaUserId });
}

/** Same shape as engineFetchAsUser, for the pre-auth email/password
 * endpoints (register, verify-email, resend-verification) - these are
 * called before any session exists, so there's no user id to forward,
 * only the internal secret proving the request came from this server
 * and not a browser talking to the engine directly (server/main.py's
 * /api/auth/* routes are gated the same way /api/users/sync is). */
export async function engineFetchAnonymous(
  path: string,
  init?: { method?: string; body?: unknown }
): Promise<NextResponse> {
  return forward(path, init ?? { method: "POST" }, {});
}

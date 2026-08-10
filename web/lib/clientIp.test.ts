import { afterEach, describe, expect, it } from "vitest";
import { clientIpHeaders, realClientIp } from "./clientIp";
import type { NextRequest } from "next/server";

// realClientIp/clientIpHeaders only ever read request.headers.get, so a
// plain Headers-backed stand-in exercises the real code path without
// needing to construct a full NextRequest (which wants an ASGI-style
// internal shape Vitest has no reason to build here).
function req(headers: Record<string, string>): NextRequest {
  return { headers: new Headers(headers) } as unknown as NextRequest;
}

const ORIGINAL_SECRET = process.env.CASTIA_INTERNAL_API_SECRET;

afterEach(() => {
  if (ORIGINAL_SECRET === undefined) delete process.env.CASTIA_INTERNAL_API_SECRET;
  else process.env.CASTIA_INTERNAL_API_SECRET = ORIGINAL_SECRET;
});

describe("realClientIp", () => {
  it("takes the first entry of x-forwarded-for - the original client, not an intermediary", () => {
    expect(realClientIp(req({ "x-forwarded-for": "203.0.113.7, 70.41.3.18, 10.0.0.1" }))).toBe(
      "203.0.113.7"
    );
  });

  it("trims whitespace around the address", () => {
    expect(realClientIp(req({ "x-forwarded-for": "  203.0.113.7  , 10.0.0.1" }))).toBe("203.0.113.7");
  });

  it("handles a single-entry x-forwarded-for with no comma", () => {
    expect(realClientIp(req({ "x-forwarded-for": "203.0.113.7" }))).toBe("203.0.113.7");
  });

  it("falls back to x-real-ip when x-forwarded-for is absent", () => {
    expect(realClientIp(req({ "x-real-ip": "203.0.113.9" }))).toBe("203.0.113.9");
  });

  it("prefers x-forwarded-for over x-real-ip when both are present", () => {
    expect(
      realClientIp(req({ "x-forwarded-for": "203.0.113.7", "x-real-ip": "203.0.113.9" }))
    ).toBe("203.0.113.7");
  });

  it("returns null rather than a placeholder when no address is available", () => {
    // A local `next dev` request over loopback often has neither header.
    // Null makes the caller omit the header entirely, so the engine uses
    // its own peer-address fallback instead of bucketing a whole
    // deployment under one literal string.
    expect(realClientIp(req({}))).toBeNull();
  });

  it("returns null for an empty or whitespace-only header rather than an empty bucket key", () => {
    expect(realClientIp(req({ "x-forwarded-for": "" }))).toBeNull();
    expect(realClientIp(req({ "x-forwarded-for": "   " }))).toBeNull();
    expect(realClientIp(req({ "x-real-ip": "   " }))).toBeNull();
  });

  it("falls through to x-real-ip when x-forwarded-for is present but blank", () => {
    expect(realClientIp(req({ "x-forwarded-for": "  ", "x-real-ip": "203.0.113.9" }))).toBe(
      "203.0.113.9"
    );
  });
});

describe("clientIpHeaders", () => {
  it("sends the address alongside the secret that makes the engine trust it", () => {
    process.env.CASTIA_INTERNAL_API_SECRET = "s3cret";
    expect(clientIpHeaders(req({ "x-forwarded-for": "203.0.113.7" }))).toEqual({
      "X-Castia-Internal-Secret": "s3cret",
      "X-Castia-Client-IP": "203.0.113.7",
    });
  });

  it("sends nothing when the internal secret isn't configured", () => {
    // server/main.py::_client_ip ignores the address without a matching
    // secret, so sending it would be pure noise.
    delete process.env.CASTIA_INTERNAL_API_SECRET;
    expect(clientIpHeaders(req({ "x-forwarded-for": "203.0.113.7" }))).toEqual({});
  });

  it("sends nothing when no client address could be determined", () => {
    process.env.CASTIA_INTERNAL_API_SECRET = "s3cret";
    expect(clientIpHeaders(req({}))).toEqual({});
  });

  it("never emits a blank address, which would bucket every visitor together", () => {
    process.env.CASTIA_INTERNAL_API_SECRET = "s3cret";
    const headers = clientIpHeaders(req({ "x-forwarded-for": "   " }));
    expect(headers["X-Castia-Client-IP"]).toBeUndefined();
  });
});

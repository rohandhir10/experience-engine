import { describe, expect, it } from "vitest";
import { scrubEvent, sharedSentryOptions } from "./sentryOptions";
import type { Breadcrumb, ErrorEvent } from "@sentry/nextjs";

// Mirrors tests/test_monitoring.py on the Python side. Same product,
// same content, same obligations - the frontend just has two extra ways
// to leak it (breadcrumbs and Session Replay), so those are what most of
// this file is about.

describe("scrubEvent", () => {
  it("drops the request body, which on this site IS the user's lyrics", () => {
    const event = {
      request: { data: "Verse 1: the copyrighted lyrics they pasted" },
    } as unknown as ErrorEvent;
    expect(scrubEvent(event).request?.data).toBeUndefined();
  });

  it("drops cookies wholesale rather than trying to pick through them", () => {
    const event = {
      request: { cookies: { "next-auth.session-token": "a-real-session" } },
    } as unknown as ErrorEvent;
    expect(scrubEvent(event).request?.cookies).toBeUndefined();
  });

  it("redacts credential headers whatever their casing", () => {
    const event = {
      request: {
        headers: {
          Authorization: "Bearer sk_live_realkey",
          "X-Castia-Internal-Secret": "the-internal-secret",
          "x-api-key": "another-one",
          "User-Agent": "Mozilla/5.0",
        },
      },
    } as unknown as ErrorEvent;
    const headers = scrubEvent(event).request?.headers as Record<string, string>;
    expect(headers.Authorization).toBe("[redacted]");
    expect(headers["X-Castia-Internal-Secret"]).toBe("[redacted]");
    expect(headers["x-api-key"]).toBe("[redacted]");
    // Non-secret headers survive - they're how you actually debug.
    expect(headers["User-Agent"]).toBe("Mozilla/5.0");
  });

  it("leaves an event with no request section alone", () => {
    const event = { message: "hi" } as unknown as ErrorEvent;
    expect(scrubEvent(event)).toEqual({ message: "hi" });
  });

  it("does not throw on unexpected shapes", () => {
    // beforeSend runs inside the SDK for every event; throwing here
    // would turn one error into two.
    for (const weird of [{}, { request: {} }, { request: { headers: null } }]) {
      expect(() => scrubEvent(weird as unknown as ErrorEvent)).not.toThrow();
    }
  });

  it("leaves no secret anywhere in the serialized payload", () => {
    const event = {
      request: {
        data: "SECRET_LYRICS",
        headers: { authorization: "Bearer SECRET_KEY" },
        cookies: { session: "SECRET_SESSION" },
      },
    } as unknown as ErrorEvent;
    const dumped = JSON.stringify(scrubEvent(event));
    for (const secret of ["SECRET_LYRICS", "SECRET_KEY", "SECRET_SESSION"]) {
      expect(dumped).not.toContain(secret);
    }
  });
});

describe("breadcrumb filtering", () => {
  const filter = sharedSentryOptions.beforeBreadcrumb;

  it("drops fetch breadcrumbs, which carry the adapt/OCR request payloads", () => {
    expect(filter({ category: "fetch" } as Breadcrumb)).toBeNull();
    expect(filter({ category: "xhr" } as Breadcrumb)).toBeNull();
  });

  it("drops console breadcrumbs, which can carry anything that was logged", () => {
    expect(filter({ category: "console" } as Breadcrumb)).toBeNull();
  });

  it("keeps the navigation trail, which is what makes a report reproducible", () => {
    const crumb = { category: "navigation" } as Breadcrumb;
    expect(filter(crumb)).toBe(crumb);
  });

  it("drops anything it doesn't explicitly recognize", () => {
    // Default-deny: a future SDK version adding a new breadcrumb type
    // should not start collecting by surprise.
    expect(filter({ category: "some.future.category" } as Breadcrumb)).toBeNull();
    expect(filter({} as Breadcrumb)).toBeNull();
  });
});

describe("the privacy locks", () => {
  it("never attaches PII automatically", () => {
    expect(sharedSentryOptions.sendDefaultPii).toBe(false);
  });

  it("keeps performance tracing off", () => {
    expect(sharedSentryOptions.tracesSampleRate).toBe(0);
  });

  it("installs the scrubber", () => {
    expect(sharedSentryOptions.beforeSend).toBe(scrubEvent);
  });
});

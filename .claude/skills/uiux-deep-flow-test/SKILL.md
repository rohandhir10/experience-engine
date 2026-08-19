---
name: uiux-deep-flow-test
description: >
  Run a full real-browser UI/UX flow test of this app (Castia,
  rohandhir10/experience-engine) using Playwright against a freshly
  stood-up local stack (Postgres, uvicorn, next start) — not just unit
  tests or a code read. Covers anonymous flows, the full auth lifecycle,
  dashboard access gating, mobile viewports, keyboard/accessibility, and
  dark mode. Use this whenever the user asks for a UI/UX audit, "test the
  app like a real user," a deep flow test, an accessibility pass, or wants
  to know if the site actually works end to end rather than just compiles.
  Findings get fixed and verified via the fix-verify-document skill —
  don't stop at a screenshot dump.
---

# UI/UX deep flow test (Castia / experience-engine)

Code reading and unit tests don't catch broken flows, missing controls, or
accessibility gaps — you have to actually drive the browser. This is the
procedure for doing that against a real local stack.

## 1. Stand up a real local stack

```bash
sudo service postgresql start
sudo -u postgres psql -c "CREATE DATABASE castia_uiux;"
export DATABASE_URL=postgresql://postgres:<pw>@localhost/castia_uiux
alembic upgrade head
nohup uvicorn server.main:app --port <scratch> > /tmp/.../uvicorn.log 2>&1 & disown
cd web && npm run build && nohup npm start -- -p <scratch2> > /tmp/.../next.log 2>&1 & disown
```

Use `chromium.launch({ executablePath: "/opt/pw-browsers/chromium" })` —
don't run `playwright install`, the browser is pre-installed.

Register and email-verify a real test user via curl (there's no email
sandbox in dev; the verification token gets written to the uvicorn log —
scrape it from there rather than guessing).

## 2. Anonymous visitor flows

Home, `/music`, `/comics`, marketing/pricing pages, and at least one
deliberately-broken URL (a bogus `/s/<id>` or `/comics/s/<id>` share
link) to confirm error states render sanely rather than blank-screening
or leaking a stack trace.

## 3. Full auth lifecycle

Sign-up → check the verification email flow actually gates login until
verified → sign-in → **sign-out** (don't skip this — it's easy to test
sign-in and never check there's an actual way to sign out) → forgot
password → reset password → sign back in with the new password. Confirm
`/dashboard` and its subpages do a real server-side redirect to
`/sign-in` when unauthenticated (`app/dashboard/layout.tsx`'s `auth()`
check) rather than a client-side flash-then-redirect that briefly exposes
authenticated content.

## 4. Signed-in dashboard flows

Every dashboard subpage (collections, settings/API keys, account data
controls) with a real signed-in session — not just that the page loads,
but that its actual controls (create, delete, export, copy-link) work.

## 5. Mobile viewport

Re-run the key flows at a real mobile viewport size (not just resizing
the window — set `viewport` in Playwright's `newPage`). Look for overflow,
tap targets that are too small/close together, and anything that only
works with a mouse hover.

## 6. Keyboard navigation & accessibility

This is the category most likely to hide real, easy-to-fix bugs:
- **Tab from a fresh page load** — what's the first stop? Is there a skip
  link, and does *activating* it (not just focusing it) actually move
  focus past the nav to real content, not just scroll the viewport? (See
  `components/SiteHeader.tsx`'s skip-link + `<span id="main-content"
  tabIndex={-1}>` pattern — landing on a scroll-only anchor without
  `tabIndex={-1}` doesn't move keyboard focus, which defeats the point.)
- Is there exactly one `<header>` landmark per page (not zero, not
  duplicated)?
- Does every page have exactly one real `<h1>`? Check error/empty states
  too — a "this link doesn't exist" page rendered as a plain `<p>` instead
  of an `<h1>` is a common miss.
- Does every page's `<title>` match what its own `<h1>` actually says? A
  page renamed on-screen but not in its `metadata.title` (or vice versa)
  is an easy, easy-to-miss inconsistency — compare each dashboard page's
  title against its own h1 directly, not by skimming the file.
- Full keyboard-only pass through at least one complete flow (no mouse) —
  confirm every interactive element is reachable and has a visible focus
  state.

## 7. Dark mode

Repeat screenshot checks (at minimum the header/skip-link and one full
page) with `colorScheme: "dark"` on the Playwright context — dark-mode
specific class branches (`dark:` Tailwind variants) are easy to get right
in light mode and silently wrong in dark.

## Capture evidence

Screenshot each finding (and its fixed state later) into a scratch
`shots/` directory — these are what justify a finding being real rather
than a hunch, and what verify a fix actually worked visually.

## Distinguish real bugs from test-script bugs

Before reporting something as an app bug, check whether it's actually your
Playwright selector being ambiguous:
- `button:has-text("Adapt")`-style selectors can match a decoy element
  (e.g. a tab-toggle button whose label happens to contain the same
  word) instead of the real submit button — inspect the actual DOM
  (`document.querySelectorAll("button")` via `page.evaluate`) when a click
  does something unexpected.
- A generic `button[type="submit"]` selector on a page with multiple forms
  (e.g. `/sign-in` rendering both a Google OAuth button and an
  email/password form) can submit the wrong form entirely — prefer
  text-scoped selectors (`button:has-text("Sign in with email")`) on pages
  with more than one submit button.

If a click navigates somewhere unexpected or nothing happens, verify it's
not your selector before writing it up as a finding.

## Tear down afterward

Always, even mid-investigation if you need to pause:
```bash
kill <uvicorn pid> <next pid>
sudo -u postgres psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='castia_uiux';"
sudo -u postgres psql -c "DROP DATABASE castia_uiux;"
sudo -u postgres psql -c "ALTER USER postgres PASSWORD NULL;"
sudo service postgresql stop
```

## After the test

List findings by severity (missing sign-out control and leaked internal
error text are the kind of thing that's ranked as high-severity here —
they're the two most severe UI/UX findings this repo has actually had).
Fix each one via the **fix-verify-document** skill — implement, test,
re-verify live in the browser with a fresh stack, screenshot the fixed
state, document in `docs/CAPABILITY_MATRIX.md`, commit.

---
name: fix-verify-document
description: >
  How we ship any non-trivial bug fix or hardening change in this repo
  (rohandhir10/experience-engine, the Castia app): investigate for the real
  root cause, fix it, prove it with tests, verify it live against a real
  local stack when it's runtime-shaped, falsify security fixes by reverting
  them, record it in docs/CAPABILITY_MATRIX.md, then commit and push. Use
  this whenever a fix is more than a one-line typo — especially for
  security, concurrency, or anything touching server/, engine/, or the
  request/response path in web/. The security-capacity-audit and
  uiux-deep-flow-test skills both hand off to this one once they've found
  something to fix; don't call a fix "done" without running this checklist.
---

# Fix, verify, document

This is the standing discipline for this repo, not a suggestion. A fix
that isn't tested, isn't verified live, and isn't written down in
`docs/CAPABILITY_MATRIX.md` is not finished — it's a diff.

## 1. Investigate for the real root cause

Don't pattern-match a fix from the symptom. Read the actual code path.
Confirm you understand *why* it's broken before writing the fix — if you
can't explain the failure mode in one sentence, keep reading. A fix aimed
at the wrong cause tends to pass its own test and still be wrong (this
happened once already in this repo: an early attempt to stop `RuntimeError`
messages from leaking to users blanket-genericized every `RuntimeError`,
which broke the *deliberately* user-facing `EngineTimeoutError` /
`ChapterTimeoutError` messages — a regression the test suite caught before
it shipped. The fix was to add explicit `except EngineTimeoutError` /
`except ChapterTimeoutError` branches *before* the generic `except
RuntimeError` branch in all four call sites, not to just soften the
first attempt).

## 2. Implement the fix

Keep it scoped to the actual problem. Don't refactor adjacent code, don't
add speculative flags or config knobs beyond what the fix needs.

## 3. Write or update automated tests

- Backend / engine changes → pytest under `tests/`. Match the existing
  descriptive-test-name style (e.g. `test_a_spoofed_leftmost_entry_does_not_win`,
  not `test_ip_1`).
- Web changes → vitest.
- If you're closing a bug, the new test should fail against the pre-fix
  code and pass against the post-fix code — that's what makes it a
  regression test rather than decoration. Verify this directly when the
  bug is subtle (see falsification, step 5).

## 4. Static verification

- Any web change: `npx tsc --noEmit` in `web/`, then a fresh production
  build (`rm -rf .next && npm run build`) — don't trust a stale `.next/`.
- Any backend change: run the relevant pytest module, then the full suite
  before calling it done (`pytest -q`).

## 5. Falsification-test security/concurrency fixes

For anything security- or race-condition-shaped, don't just trust that the
new test passes — prove it would have failed before the fix:

```
git stash push -- <changed file>   # temporarily revert just the fix
pytest tests/test_whatever.py -q -k <the new test>   # confirm it FAILS
git stash pop                                        # restore the fix
pytest tests/test_whatever.py -q -k <the new test>   # confirm it PASSES
```

This caught a real one: without the Postgres advisory lock in
`server/db.py::migrate_to_head`, concurrent `alembic upgrade head` calls
didn't error cleanly — they hung indefinitely (a stuck idle-in-transaction
lock), which is worse than a crash. That only became visible by actually
reverting the fix and running the concurrency test against it.

## 6. Live verification for runtime/integration-shaped bugs

Unit tests don't catch everything (auth cookies, real Postgres constraint
behavior, actual HTTP round-trips, migration ordering). When the bug is
one of those, stand up a real local stack and hit it for real:

```bash
sudo service postgresql start
# set a throwaway password, then:
sudo -u postgres psql -c "CREATE DATABASE castia_<scratch>;"
export DATABASE_URL=postgresql://postgres:<pw>@localhost/castia_<scratch>
alembic upgrade head
nohup uvicorn server.main:app --port <scratch-port> > /tmp/.../uvicorn.log 2>&1 & disown
cd web && nohup npm run build && npm start -- -p <scratch-port> > /tmp/.../next.log 2>&1 & disown
```

Register and verify a real test user via curl + scraping the verification
token out of the log (there's no email sandbox in dev — the token gets
logged). Drive the actual flow with curl/Playwright, not assumptions.

**Bash gotcha**: compound `export ... && nohup ... &` one-liners have
silently failed to start the process at least twice in this repo's history
— no log file, no error. If a backgrounded process doesn't show up, split
`export` and `nohup ... & disown` into separate Bash calls.

**Always tear down afterward**, even if you're in a hurry:
```bash
kill <uvicorn pid> <next pid>
sudo -u postgres psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='castia_<scratch>';"
sudo -u postgres psql -c "DROP DATABASE castia_<scratch>;"
sudo -u postgres psql -c "ALTER USER postgres PASSWORD NULL;"
sudo service postgresql stop
```
If `DROP DATABASE` fails with "being accessed by other users", re-run the
`pg_terminate_backend` line immediately before retrying — a lingering
connection from the process you just killed is the usual cause.

## 7. Record it in docs/CAPABILITY_MATRIX.md

Add a new `##`-headed entry: what was found (be honest about severity —
don't undersell or oversell), what was fixed (with the actual file/symbol
names), and a `**Verified:**` paragraph describing exactly how (which
tests, and what the live verification showed). Future readers — including
future you — rely on this doc being an honest record, not marketing copy.

## 8. Commit and push

One commit per discrete piece of work, clear message explaining *why*, on
the current working branch. Don't batch unrelated fixes into one commit.

## Why this order matters

Steps 3-6 are deliberately redundant with each other (unit tests +
falsification + live verification) because each catches a different class
of failure: unit tests catch logic errors, falsification catches "my test
would have passed anyway" false confidence, live verification catches
integration-only bugs that no amount of mocking will surface. Skipping any
one of them has already cost real debugging time in this repo — that's why
all three are here, not because it's a formality.

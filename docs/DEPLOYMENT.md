# Deploying CASTIA + enabling sign-in

Two services, plus one thing only a human with a Google account can do.

| Piece | Where it runs | What it needs |
| --- | --- | --- |
| Engine API (`server/`, `engine/`) | Railway (persistent container) | `OPENAI_API_KEY`, `DATABASE_URL`, `CASTIA_INTERNAL_API_SECRET` |
| Web app (`web/`) | Vercel | `CASTIA_ENGINE_API_URL`, `AUTH_SECRET`, `AUTH_GOOGLE_ID`, `AUTH_GOOGLE_SECRET`, `CASTIA_INTERNAL_API_SECRET` |
| Google OAuth client | Google Cloud Console | created by hand, once |

Full variable lists live in `.env.example` (engine) and `web/.env.example`.

## 1. Google OAuth client — do this first

Nothing about sign-in works without it, and it cannot be automated.

1. https://console.cloud.google.com → APIs & Services → Credentials
2. **Create Credentials → OAuth client ID → Web application**
3. Authorized redirect URI, **exactly**:
   - `https://<your-vercel-domain>/api/auth/callback/google`
   - and `http://localhost:3000/api/auth/callback/google` for local dev
4. Copy the client ID and secret.

> The single most common first-attempt failure is `redirect_uri_mismatch`.
> The URI must match character for character — no trailing slash, `https`
> not `http` in production, and the `/api/auth/callback/google` path is
> fixed by Auth.js, not something to shorten.

If the consent screen is in "Testing" mode, only accounts listed as test
users can sign in. That is usually what "it worked for me but not for
them" means.

## 2. Generate the two secrets

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"   # AUTH_SECRET
python3 -c "import secrets; print(secrets.token_urlsafe(32))"   # CASTIA_INTERNAL_API_SECRET
```

`CASTIA_INTERNAL_API_SECRET` goes on **both** services and must be
byte-identical. See §5 for what happens when it isn't.

## 3. Railway (engine)

Set `OPENAI_API_KEY`, `DATABASE_URL` (the Postgres plugin's connection
string), `CASTIA_INTERNAL_API_SECRET`, and `CASTIA_ALLOWED_ORIGINS` (your
Vercel domain).

On boot the service runs `alembic upgrade head`
(`server/db.py::migrate_to_head`). The baseline revision is
`checkfirst`, so it is safe against both an empty database and the
already-deployed one — no manual `alembic stamp` step.

Check afterwards:

- `GET /health` → `{"status":"ok"}`
- `GET /health/db` → `{"status":"ok"}` (503 means `DATABASE_URL` is wrong
  or Postgres is unreachable — accounts will be entirely off)
- Startup log should say `database schema at migration head`

## 4. Vercel (web)

Set `CASTIA_ENGINE_API_URL` to the Railway public domain, plus the four
auth variables. Redeploy after adding them — Vercel does not apply new
env vars to an existing build.

`AUTH_URL` is not needed; Auth.js v5 infers the deployment URL on Vercel.

## 5. Testing sign-in, and reading the failures

Visit `/sign-in`. What you see tells you where you are:

| Symptom | Meaning |
| --- | --- |
| "Accounts aren't live yet" | `AUTH_SECRET` or `AUTH_GOOGLE_ID` missing on Vercel |
| `redirect_uri_mismatch` from Google | §1, step 3 |
| Signed in, but no history ever appears | **`CASTIA_INTERNAL_API_SECRET` differs between the two services** |
| Signed in, history empty, engine logs `user sync failed: 503` | `DATABASE_URL` unset on Railway |

That third row is the one worth internalising: a mismatched internal
secret produces a sign-in that looks completely successful. The engine
ignores the forwarded user id (`server/main.py::_authed_user_id` requires
the secret to match), so every adaptation is recorded anonymously and the
dashboard stays empty forever, with no error anywhere. If sign-in works
but nothing saves, check this before anything else.

Then, end to end:

1. Sign in with Google → should land on `/dashboard`
2. Adapt a song → it should appear under Recent Adaptations
3. Star it → check `/dashboard/favorites`
4. "Add to…" → New collection → check `/dashboard/collections`
5. Open the song's `/s/<id>` link in a private window while signed in as
   a *different* account, then star it — it should save to that account's
   history without touching the first account's row

## What has never been verified

Every backend path here is covered by tests against a real database
(`tests/test_accounts.py`), and `next build` proves the wiring compiles.
**The Google OAuth round-trip itself has never been executed in any
environment** — not locally, not on a deploy. Step 1 above is where to
expect friction on the first attempt, not the account features behind it.

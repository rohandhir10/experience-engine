# Vendored copy — deployment-only

`engine/` and `server/` in this directory are copies of the packages at
the repo root, vendored here because Vercel's `experience-engine` project
has its Root Directory set to `web/` — its build has no visibility into
files outside that directory, so the Python engine has to physically
live inside `web/` for `web/api/engine.py` (the Vercel Python function)
to import it at all.

**This is a real, disclosed duplication, not an accident.** The repo
root `engine/`/`server/` remain the canonical source — used by the CLI
(`python -m engine.cli`), the test suite, the benchmark tooling, and the
Docker/uvicorn deployment (`Dockerfile`). This copy exists only so the
Vercel deployment can see the same code.

One deliberate fork: `server/cache.py` here writes to `/tmp` instead of
next to itself, because the deployed Vercel bundle is read-only at
runtime. See that file's docstring for what that costs (best-effort,
per-instance caching only, not durable across cold starts).

**Keeping this in sync:** until this deployment shape is replaced with
something that doesn't need a duplicate (a proper shared package, or a
separately-hosted backend the Docker image already supports), re-copy
after any change to the root `engine/`/`server/`:

```
rm -rf web/api/_vendor/engine web/api/_vendor/server
cp -r engine web/api/_vendor/engine
cp -r server web/api/_vendor/server
find web/api/_vendor -name "__pycache__" -exec rm -rf {} +
```

Then reapply the `server/cache.py` /tmp fork (the diff is small — see
git history) and the docstring note at the top of `server/main.py`.

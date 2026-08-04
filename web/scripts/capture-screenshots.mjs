#!/usr/bin/env node
// Captures real screenshots of the actual running app, used on the main
// homepage (components/InputScreen.tsx) and app/alternate-homepage/page.tsx
// — the deliberate alternative to fabricated/AI-generated "product
// screenshots." Every image this produces is a real render of real UI,
// targeted via a handful of inert `data-screenshot="..."` attributes added
// to the real components (InputScreen.tsx, ComparisonCard.tsx,
// app/dashboard/page.tsx) specifically so this script has something
// stable to select, instead of guessing at CSS classes that change with
// every redesign.
//
// Usage: npm run build && node scripts/capture-screenshots.mjs
// (build first - this starts `next start`, which needs a build to exist)
//
// Known limitation, stated plainly: these are a snapshot. Nothing
// re-runs this automatically when the UI changes, so the images in
// public/screenshots/ can silently drift out of date the same way any
// hand-maintained screenshot library can. Re-run this script after any
// visual change to InputScreen.tsx, ComparisonCard.tsx, or
// app/dashboard/page.tsx and commit the new PNGs alongside that change.
import { chromium } from "playwright";
import { spawn } from "node:child_process";
import { mkdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const OUT_DIR = path.join(ROOT, "public", "screenshots");
const PORT = 3177;
const BASE_URL = `http://localhost:${PORT}`;

function waitForServer(url, timeoutMs = 20_000) {
  const deadline = Date.now() + timeoutMs;
  return new Promise((resolve, reject) => {
    const attempt = async () => {
      try {
        const res = await fetch(url);
        if (res.ok || res.status < 500) return resolve();
      } catch {
        // not up yet
      }
      if (Date.now() > deadline) return reject(new Error(`Server didn't come up at ${url}`));
      setTimeout(attempt, 400);
    };
    attempt();
  });
}

async function main() {
  mkdirSync(OUT_DIR, { recursive: true });

  const server = spawn(
    "npx",
    ["next", "start", "-p", String(PORT)],
    {
      cwd: ROOT,
      env: {
        ...process.env,
        AUTH_SECRET: process.env.AUTH_SECRET || "capture-script-placeholder",
        AURA_ENGINE_API_URL: process.env.AURA_ENGINE_API_URL || "http://localhost:1",
      },
      stdio: "ignore",
    }
  );

  try {
    await waitForServer(BASE_URL);

    const browser = await chromium.launch({ executablePath: "/opt/pw-browsers/chromium" });
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });

    // Homepage hero — headline, language pickers, textarea, submit.
    await page.goto(`${BASE_URL}/`, { waitUntil: "networkidle" });
    await page.waitForTimeout(400);
    await page.locator('[data-screenshot="hero"]').screenshot({
      path: path.join(OUT_DIR, "hero.png"),
    });
    await page.locator('[data-screenshot="language-chips"]').screenshot({
      path: path.join(OUT_DIR, "language-chips.png"),
    });

    // The real demo result — one full literal/adapted/why comparison
    // card, not a fabricated mockup.
    await page.goto(`${BASE_URL}/s/demo`, { waitUntil: "networkidle" });
    await page.waitForTimeout(400);
    await page.locator('[data-screenshot="comparison-card"]').screenshot({
      path: path.join(OUT_DIR, "comparison-card.png"),
    });

    // The dashboard's sidebar + workspace, cropped to exclude "Recent
    // Adaptations" — that section shows a sign-in prompt when
    // unauthenticated (this script never signs in), which would be an
    // honest but unflattering/uninformative thing to include. The
    // sidebar, header, language pickers, and lyric box all render fully
    // regardless of auth state, so this crop needs no fabricated
    // signed-in data to be a real, representative screenshot.
    await page.goto(`${BASE_URL}/dashboard`, { waitUntil: "networkidle" });
    await page.waitForTimeout(400);
    const workspaceBox = await page.locator('[data-screenshot="dashboard-workspace"]').boundingBox();
    const recentBox = await page.locator('[data-screenshot="dashboard-recent-boundary"]').boundingBox();
    if (workspaceBox && recentBox) {
      const padding = 16;
      await page.screenshot({
        path: path.join(OUT_DIR, "dashboard-workspace.png"),
        clip: {
          x: Math.max(workspaceBox.x - padding, 0),
          y: Math.max(workspaceBox.y - padding, 0),
          width: workspaceBox.width + padding * 2,
          height: recentBox.y - workspaceBox.y + padding,
        },
      });
    } else {
      throw new Error("Could not locate dashboard-workspace/dashboard-recent-boundary markers");
    }

    await browser.close();
    console.log(`Wrote screenshots to ${OUT_DIR}`);
  } finally {
    server.kill("SIGTERM");
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});

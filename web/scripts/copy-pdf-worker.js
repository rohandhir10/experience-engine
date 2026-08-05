// pdfjs-dist ships its worker as an ESM (.mjs) bundle that Next's
// webpack config doesn't know how to treat as a static asset - pointing
// at it via `new URL(..., import.meta.url)` (the usual bundler pattern)
// makes Next's minifier try to parse and re-minify it as a normal JS
// module instead of copying it untouched, which fails on `import.meta`
// inside an already-minified file ("'import.meta' cannot be used outside
// of module code"). Copying it into public/ and referencing it by a
// plain string path (lib/pdfToImages.ts) sidesteps the bundler
// entirely. Wired into postinstall, predev, and prebuild (package.json)
// so it can't drift out of sync with whatever pdfjs-dist version is
// actually installed, or go missing on a cached-node_modules CI run
// that skips postinstall. Not committed (web/.gitignore) since it's
// this script's output, not source.
const fs = require("fs");
const path = require("path");

// The "legacy" build, not the default modern one - pdfjs-dist 6.x's
// modern build uses very new JS engine features (observed: Map.prototype
// .getOrInsertComputed, part of a proposal barely landing in browsers as
// of 2026) that threw "is not a function" on real, current browser
// versions during testing. legacy/ targets a wider compatibility range,
// which is the point of it existing at all.
const src = require.resolve("pdfjs-dist/legacy/build/pdf.worker.min.mjs");
const dest = path.join(__dirname, "..", "public", "pdf.worker.min.mjs");

fs.copyFileSync(src, dest);
console.log(`Copied pdf.worker.min.mjs -> ${path.relative(process.cwd(), dest)}`);

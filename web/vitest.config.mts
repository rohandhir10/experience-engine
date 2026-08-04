import { defineConfig } from "vitest/config";
import path from "path";

// First real test harness for the web/ package - until this existed,
// every TS change was verified by `tsc --noEmit` and `next build` only,
// which catch type errors but not behavior (flagged as a coverage gap in
// docs/CAPABILITY_MATRIX.md more than once). Scope today: pure logic in
// lib/ (no jsdom, no component rendering) - the highest-value tests per
// unit of setup, since lib/ holds the language detector and the API
// polling flow. Component tests would need jsdom + testing-library;
// worth adding when a component regression actually bites.
export default defineConfig({
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "."),
    },
  },
  test: {
    include: ["lib/**/*.test.ts"],
  },
});

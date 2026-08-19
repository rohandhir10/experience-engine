import { FlatCompat } from "@eslint/eslintrc";

const compat = new FlatCompat({ baseDirectory: import.meta.dirname });

const eslintConfig = [
  {
    // Vendored/generated output, not source this project owns the style
    // of - public/pdf.worker.min.mjs is a minified third-party build
    // artifact copied in by scripts/copy-pdf-worker.js (see that
    // script's own comment), and scripts/ is plain Node tooling that
    // predates and sits outside the Next app's TS/ESM conventions.
    ignores: [".next/**", "public/**", "scripts/**"],
  },
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    rules: {
      // This is the first time eslint-config-next has run against this
      // codebase (it was never installed before the Next 15 upgrade),
      // and this rule flags ~300 pre-existing literal ' and " characters
      // in JSX text across the app - a cosmetic HTML-entity-escaping
      // preference, not a correctness issue. Fixing all of them is a
      // separate cleanup, not part of restoring `next lint`.
      "react/no-unescaped-entities": "off",
    },
  },
];

export default eslintConfig;

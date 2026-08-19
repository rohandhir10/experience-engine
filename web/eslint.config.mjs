import nextConfig from "eslint-config-next";

const eslintConfig = [
  {
    // Vendored/generated output, not source this project owns the style
    // of - public/pdf.worker.min.mjs is a minified third-party build
    // artifact copied in by scripts/copy-pdf-worker.js (see that
    // script's own comment), and scripts/ is plain Node tooling that
    // predates and sits outside the Next app's TS/ESM conventions.
    // eslint-config-next's own flat config already ignores .next/**.
    ignores: ["public/**", "scripts/**"],
  },
  ...nextConfig,
  {
    rules: {
      // This is the first time eslint-config-next has run against this
      // codebase (it was never installed before the Next 15 upgrade),
      // and this rule flags ~300 pre-existing literal ' and " characters
      // in JSX text across the app - a cosmetic HTML-entity-escaping
      // preference, not a correctness issue. Fixing all of them is a
      // separate cleanup, not part of restoring lint.
      "react/no-unescaped-entities": "off",

      // New in the eslint-config-next 16 upgrade's bundled eslint-plugin-
      // react-hooks (a React Compiler-oriented rule). It flags 6
      // pre-existing call sites here, all the same legitimate shape: a
      // mount-only effect (`useEffect(() => { ... }, [])`) reading
      // client-only state (localStorage via readMediumPreference/
      // readStoredTheme, matchMedia's reduced-motion query, or a
      // synchronous demo-data shortcut) and syncing it into state once,
      // after hydration - the standard way to avoid an SSR/client
      // mismatch. The rule's own suggested alternative doesn't fit any of
      // these (there's no non-effect way to read browser-only APIs after
      // mount), so silencing it here beats either refactoring 6 working,
      // correct call sites or leaving lint broken again.
      "react-hooks/set-state-in-effect": "off",
    },
  },
];

export default eslintConfig;

import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        serif: [
          "Iowan Old Style",
          "Palatino Linotype",
          "Georgia",
          "ui-serif",
          "serif",
        ],
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          "Inter",
          "Segoe UI",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
      },
      colors: {
        paper: {
          DEFAULT: "#fbfaf8",
          // Warm near-black, not the cold blue-black every AI-tool dark
          // mode defaults to (OpenAI/Anthropic/Midjourney/every Vercel
          // template) - real feedback: the pitch-black + neon-purple
          // combination reads as "ML infra tool," not "creative space."
          // A warm brown-black plus the terracotta accent below is a
          // small, systemic change (every dark-mode surface site-wide
          // picks it up, not a homepage-only patch) toward something
          // that feels analog rather than synthetic.
          dark: "#181310",
        },
        ink: {
          DEFAULT: "#1a1a1a",
          dark: "#ededec",
        },
        accent: {
          // Was #5b5bd6 (indigo/purple) - the single most recognizable
          // "AI startup" tell named in the feedback. Warm terracotta/
          // copper instead: still a confident, saturated accent, but one
          // that reads as vinyl-sleeve/analog rather than neon-glow.
          DEFAULT: "#b8562e",
        },
      },
      maxWidth: {
        prose: "42rem",
      },
      // Tailwind's default opacity scale only defines multiples of 5
      // (…/60, /65, /70…) - a slash value outside that scale (e.g.
      // text-ink/62) silently generates NO CSS at all, no build error,
      // no warning. That's a real bug this site hit: several rounds of
      // contrast fixes landed on odd values like /62, /68, /72, /78 (a
      // sweep script's rounding), and every one of those classes was
      // dropped from the compiled stylesheet - the element just fell
      // back to whichever OTHER color utility on it still compiled
      // (e.g. only the light-mode `text-ink/75` half of a
      // "text-ink/75 dark:text-white/62" pair), which is exactly how
      // text ends up rendering in the wrong theme's color and blending
      // into the background. Filling in every integer 0-100 here means
      // any `/NN` slash value already written anywhere in the codebase
      // compiles, and this can't happen again for a future value either.
      opacity: Object.fromEntries(
        Array.from({ length: 101 }, (_, n) => [String(n), String(n / 100)])
      ),
    },
  },
  // Class-based, not "media": a manual toggle (components/ThemeToggle.tsx)
  // needs to override the OS preference, which "media" can't do. The
  // `dark` class is set on <html> by lib/theme.ts's THEME_INIT_SCRIPT
  // (inlined into app/layout.tsx, before hydration) and by the toggle
  // itself, defaulting to prefers-color-scheme when nothing is stored yet.
  darkMode: "class",
  plugins: [],
};

export default config;

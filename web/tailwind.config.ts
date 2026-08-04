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
    },
  },
  darkMode: "media",
  plugins: [],
};

export default config;

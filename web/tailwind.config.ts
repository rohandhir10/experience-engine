import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        serif: ["Georgia", "ui-serif", "serif"],
        sans: ["DM Sans", "sans-serif"],
        display: ["Manrope", "sans-serif"],
        mono: ["DM Mono", "monospace"],
      },
      colors: {
        paper: {
          DEFAULT: "#f6f3ed",
          dark: "#19171f",
        },
        ink: {
          DEFAULT: "#19171f",
          dark: "#f8f4fb",
        },
        accent: {
          DEFAULT: "#a28aff",
        },
      },
      maxWidth: {
        prose: "42rem",
      },
      opacity: Object.fromEntries(
        Array.from({ length: 101 }, (_, n) => [String(n), String(n / 100)])
      ),
    },
  },
  darkMode: "class",
  plugins: [],
};

export default config;

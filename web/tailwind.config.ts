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
          dark: "#0b0b0c",
        },
        ink: {
          DEFAULT: "#1a1a1a",
          dark: "#ededec",
        },
        accent: {
          DEFAULT: "#5b5bd6",
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

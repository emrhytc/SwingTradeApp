/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        surface: {
          DEFAULT: "#0f1117",
          card: "#161b27",
          border: "#1e2535",
          hover: "#1c2233",
        },
        suitable: {
          DEFAULT: "#22c55e",
          dim: "#16a34a22",
        },
        cautious: {
          DEFAULT: "#f59e0b",
          dim: "#d9770622",
        },
        danger: {
          DEFAULT: "#ef4444",
          dim: "#dc262622",
        },
        accent: "#6366f1",
        muted: "#6b7280",
      },
      fontFamily: {
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
    },
  },
  plugins: [],
};

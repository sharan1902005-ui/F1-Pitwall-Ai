/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      colors: {
        pit: {
          black: "#08090d",
          panel: "#10131a",
          panel2: "#161b24",
          line: "#2a3140",
          red: "#ff314f",
          blue: "#39a9ff",
          green: "#38d996",
          yellow: "#f5c542",
          purple: "#b66cff",
        },
      },
      boxShadow: {
        telemetry: "0 18px 60px rgba(0,0,0,0.35)",
      },
    },
  },
  plugins: [],
};

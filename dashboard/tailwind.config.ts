import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        agent: {
          bg: "#0a0a0f",
          card: "#12121a",
          border: "#1e1e2e",
          accent: "#6366f1",
          green: "#22c55e",
          red: "#ef4444",
          yellow: "#eab308",
          cyan: "#06b6d4",
        },
      },
    },
  },
  plugins: [],
};
export default config;

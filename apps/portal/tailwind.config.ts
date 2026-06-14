import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Veeam brand palette
        veeam: {
          green: "#00B336",
          dark: "#1A1A2E",
          gray: "#F4F6F8",
        },
      },
    },
  },
  plugins: [],
};

export default config;

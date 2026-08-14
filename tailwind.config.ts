import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        pokeyellow: "#FFCB05",
        pokeblue: "#5b9fd4",
        pokeblueDark: "#7eb8e8",
        surface: {
          DEFAULT: "#0f1419",
          raised: "#1a2332",
          muted: "#243044",
        },
      },
    },
  },
  plugins: [],
};

export default config;

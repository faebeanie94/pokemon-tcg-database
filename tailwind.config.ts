import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        pokeyellow: "#FFCB05",
        pokeblue: "#3D7DCA",
        pokeblueDark: "#003A70",
      },
    },
  },
  plugins: [],
};

export default config;

/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        // identidade Brasil: verde-bandeira como acento editorial
        brasil: "#009739",
        brasildark: "#00672a",
        amarelo: "#FEDD00",
        ink: "#0a120c", // fundo escuro com tinta verde (não preto puro)
        panel: "#121c14",
        panel2: "#1a261c",
        hair: "#27402c",
      },
      fontFamily: {
        display: ['"Georgia"', "ui-serif", "serif"],
        sans: ['"Inter"', "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};

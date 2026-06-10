/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        // paleta institucional clara
        petrol: "#0F4C5C", // azul petróleo — títulos, números, ações
        petroldark: "#0A3742",
        azul: "#4EA5D9", // azul claro — acento secundário
        azuldark: "#2F86B8",
        ambar: "#E8910C", // destaque (âmbar levemente mais quente)
        texto: "#41505F", // cinza-azulado para texto
        bg: "#E4EAF0", // fundo da página (cinza-azul calmo, sem estourar)
        card: "#F4F7FA", // superfícies (off-white suave, não branco puro)
        cardhi: "#FBFCFD", // realce pontual (hover de linha)
        hair: "#D3DCE5", // bordas finas
      },
      fontFamily: {
        display: ['"Georgia"', "ui-serif", "serif"],
        sans: ['"Inter"', "system-ui", "sans-serif"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(15,76,92,0.05), 0 6px 20px rgba(15,76,92,0.06)",
      },
    },
  },
  plugins: [],
};

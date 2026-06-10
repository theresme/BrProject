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
        ambar: "#F59E0B", // destaque
        texto: "#4B5563", // cinza texto
        bg: "#F5F7FA", // fundo da página
        card: "#FFFFFF", // superfícies
        hair: "#E3E8EF", // bordas finas
      },
      fontFamily: {
        display: ['"Georgia"', "ui-serif", "serif"],
        sans: ['"Inter"', "system-ui", "sans-serif"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(15,76,92,0.04), 0 4px 16px rgba(15,76,92,0.05)",
      },
    },
  },
  plugins: [],
};

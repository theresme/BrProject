import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // proxy do dev p/ o backend FastAPI, evita CORS local
      "/api": "http://localhost:8000",
    },
  },
  build: {
    // build direto para a pasta servida pelo FastAPI em produção
    outDir: "../backend/static",
    emptyOutDir: true,
  },
});

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Baut die Lovelace-Card als eine einzige IIFE-Datei (React inklusive):
// dist/hausmeister-card.js → nach config/www/ kopieren, fertig.
export default defineConfig({
  plugins: [react()],
  // Reacts CommonJS-Build referenziert process.env.NODE_ENV — in der
  // IIFE-Lib gibt es kein `process`, daher hier ersetzen.
  define: {
    "process.env.NODE_ENV": JSON.stringify("production"),
  },
  build: {
    lib: {
      entry: "src/main.js",
      formats: ["iife"],
      name: "HausmeisterCard",
      fileName: () => "hausmeister-card.js",
    },
    outDir: "dist",
    cssCodeSplit: false,
  },
});

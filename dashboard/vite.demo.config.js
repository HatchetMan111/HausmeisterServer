import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Baut die Demo-Seite (Mock-Daten) statisch nach dist-demo/ —
// praktisch für Tests ohne Dev-Server (kein File-Watching nötig).
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: "dist-demo",
    rollupOptions: { input: "index.html" },
  },
});

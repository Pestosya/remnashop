import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The SPA is served by FastAPI under /app (see src/web/app.py), so every asset
// URL has to be built against that base.
export default defineConfig({
  base: "/app/",
  plugins: [react()],
  build: {
    outDir: "dist",
    emptyOutDir: true,
    // Telegram's in-app browsers are current Chromium/WebKit; no legacy target
    // is needed, and a modern one keeps the bundle small.
    target: "es2020",
  },
  server: {
    port: 5173,
    // `npm run dev` against a locally running backend.
    proxy: {
      "/api": {
        target: process.env.VITE_API_TARGET ?? "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});

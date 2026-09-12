import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In development, the Vite dev server proxies API calls to the FastAPI
// backend so the frontend can use relative "/api/..." URLs everywhere
// (same-origin, no CORS) - both here and in production, where FastAPI
// serves the built app directly.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});

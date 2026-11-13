import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwind from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwind()],
  server: {
    strictPort: true,
    proxy: {
      "/api": {
        target: process.env.VITE_API_PROXY ?? "http://localhost:8000",
        headers: process.env.VITE_PREVIEW_SECRET ? { "X-Preview-Proxy": process.env.VITE_PREVIEW_SECRET } : {},
      },
    },
  },
});

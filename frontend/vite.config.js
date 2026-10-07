import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "localhost",
    port: 5173,
    strictPort: true,
    // Für öffentliche Vorschauen können zusätzliche Hostnamen explizit erlaubt werden.
    allowedHosts: (process.env.VITE_ALLOWED_HOSTS || "localhost,127.0.0.1")
      .split(",")
      .map((h) => h.trim())
      .filter(Boolean),
    proxy: {
      "/challenge": {
        target: process.env.VITE_API_PROXY_TARGET || "http://localhost:8000",
        changeOrigin: true,
      },
      "/community": {
        target: process.env.VITE_API_PROXY_TARGET || "http://localhost:8000",
        changeOrigin: true,
      },
      // Lokaler Standard: Frontend und FastAPI laufen getrennt mit HMR bzw. Reload.
      // Eine öffentliche API kann über VITE_API_PROXY_TARGET aktiviert werden.
      "/auth": {
        target: process.env.VITE_API_PROXY_TARGET || "http://localhost:8000",
        changeOrigin: true,
        secure: false,
      },
      "/users": {
        target: process.env.VITE_API_PROXY_TARGET || "http://localhost:8000",
        changeOrigin: true,
        secure: false,
      },
      "/activities": {
        target: process.env.VITE_API_PROXY_TARGET || "http://localhost:8000",
        changeOrigin: true,
        secure: false,
      },
      "/admin": {
        target: process.env.VITE_API_PROXY_TARGET || "http://localhost:8000",
        changeOrigin: true,
        secure: false,
        // /admin is also a React page. Only API requests belong to FastAPI.
        bypass(req) {
          const path = (req.url || "").split("?")[0];
          if (
            ["/admin", "/admin/"].includes(path) &&
            req.headers.accept?.includes("text/html")
          ) {
            return "/index.html";
          }
        },
      },
    },
  },
});

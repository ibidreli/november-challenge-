import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    // erlaubt Verbindungen von anderen Hosts (ngrok host header)
    host: true,
    port: 5173,
    // explizit erlaubte Hostnamen — kann per ENV überschrieben werden (VITE_ALLOWED_HOSTS, komma‑separiert)
    allowedHosts: (process.env.VITE_ALLOWED_HOSTS || "localhost,127.0.0.1,ollie-strict-bimonthly.ngrok-free.dev,november-challenge.onrender.com")
      .split(",").map(h => h.trim()).filter(Boolean),
    proxy: {
      // verwende VITE_API_BASE_URL während der Entwicklung, falls gesetzt,
      // ansonsten Fallback auf deine Render‑Domain (kein localhost)
      "/auth": {
        target: process.env.VITE_API_BASE_URL ? process.env.VITE_API_BASE_URL : "https://november-challenge.onrender.com",
        changeOrigin: true,
        secure: false
      },
      "/users": {
        target: process.env.VITE_API_BASE_URL ? process.env.VITE_API_BASE_URL : "https://november-challenge.onrender.com",
        changeOrigin: true,
        secure: false
      },
      "/activities": {
        target: process.env.VITE_API_BASE_URL ? process.env.VITE_API_BASE_URL : "https://november-challenge.onrender.com",
        changeOrigin: true,
        secure: false
      },
      "/admin": {
        target: process.env.VITE_API_BASE_URL ? process.env.VITE_API_BASE_URL : "https://november-challenge.onrender.com",
        changeOrigin: true,
        secure: false
      },
    },
  },
});
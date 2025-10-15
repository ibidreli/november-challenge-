import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    // erlaubt Verbindungen von anderen Hosts (ngrok host header)
    host: true,
    port: 5173,
    // explizit erlaubte Hostnamen — füge hier weitere ngrok-Hosts hinzu, falls nötig
    allowedHosts: [
      "localhost",
      "127.0.0.1",
      "ollie-strict-bimonthly.ngrok-free.dev"
    ],
    proxy: {
      // leitet /auth, /users, /activities an dein Backend weiter
      "/auth": "http://localhost:8000",
      "/users": "http://localhost:8000",
      "/activities": "http://localhost:8000",
    },
  },
});
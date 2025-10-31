import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";
import axios from "axios";

axios.defaults.withCredentials = true;

// API-Basis aus URL-Param, sonst aus ENV, und auf HTTPS erzwingen
(function () {
  try {
    const qs =
      window.location.search ||
      (window.location.hash.startsWith("#") ? window.location.hash.slice(1) : "");
    const p = new URLSearchParams(qs);

    let base =
      p.get("backend_base_https") ||
      p.get("backend_base") ||
      (import.meta.env.VITE_API_BASE_URL ||
        "https://november-challenge.onrender.com");

    if (!/^https?:\/\//i.test(base)) base = "https://" + base;
    base = base.replace(/^http:\/\//i, "https://").replace(/\/$/, "");

    axios.defaults.baseURL = base; // global
    window.__API_BASE__ = base; // optional fürs Debuggen
    console.log("API Base URL set to:", base);
  } catch (e) {
    console.error("Error setting API base URL:", e);
    axios.defaults.baseURL = "https://november-challenge.onrender.com";
  }
})();

// Token aus URL lesen & als Bearer mitschicken (hilft bei Mobile/Inkognito)
(function () {
  const raw =
    window.location.search ||
    (window.location.hash.startsWith("#") ? window.location.hash.slice(1) : "");
  if (raw) {
    const p = new URLSearchParams(raw);
    const t = p.get("access_token");
    if (t) {
      sessionStorage.setItem("nc_token", t);
      // optional: access_token aus der URL entfernen
      try {
        const url = new URL(window.location.href);
        url.searchParams.delete("access_token");
        history.replaceState({}, "", url.toString());
      } catch {}
    }
  }
  // Axios-Interceptor: wenn Token vorhanden, als Authorization senden
  axios.interceptors.request.use((cfg) => {
    const t = sessionStorage.getItem("nc_token");
    if (t) {
      cfg.headers = { ...(cfg.headers || {}), Authorization: `Bearer ${t}` };
    }
    return cfg;
  });
})();

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";
import axios from "axios";
axios.defaults.withCredentials = true;

// API-Basis aus URL-Param, sonst aus ENV, und auf HTTPS erzwingen
(function () {
  const qs = window.location.search || (window.location.hash.startsWith("#") ? window.location.hash.slice(1) : "");
  const p = new URLSearchParams(qs);
  let base =
    p.get("backend_base_https") ||
    p.get("backend_base") ||
    (import.meta.env.VITE_API_BASE_URL || "https://november-challenge.onrender.com");

  if (!/^https?:\/\//i.test(base)) base = "https://" + base;
  base = base.replace(/^http:\/\//i, "https://").replace(/\/$/, "");

  axios.defaults.baseURL = base;            // <— global setzen
  window.__API_BASE__ = base;               // optional fürs Debuggen
})();

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

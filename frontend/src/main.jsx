import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";

// Remove credentials left by the previous OAuth flow, without reusing them.
try {
  sessionStorage.removeItem("nc_token");
} catch {
  /* Public views also work when browser storage is blocked. */
}
const clean = new URL(window.location.href);
for (const key of [
  "access_token",
  "refresh_token",
  "backend_base",
  "backend_base_https",
])
  clean.searchParams.delete(key);
if (/(?:access_token|refresh_token)=/.test(clean.hash)) clean.hash = "";
history.replaceState({}, "", clean);

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

import axios from "axios";
import { previewRequest } from "./previewData";

export const isPreview = import.meta.env.VITE_UI_PREVIEW === "true";
export const apiBase = (import.meta.env.VITE_API_BASE_URL || "").replace(
  /\/$/,
  "",
);
const client = axios.create({
  baseURL: apiBase,
  withCredentials: true,
  timeout: 30000,
});
const pendingPublicReads = new Map();
export function api(path, { method = "GET", body, admin = false } = {}) {
  const headers = admin
    ? { "X-Admin-Token": localStorage.getItem("nc_admin") || "" }
    : {};
  const publicRead =
    method === "GET" &&
    !admin &&
    ["/challenge", "/challenge/statistics", "/users/"].includes(path);
  if (publicRead && pendingPublicReads.has(path))
    return pendingPublicReads.get(path);
  const request = isPreview
    ? previewRequest(path, method, body)
    : client
        .request({ url: path, method, data: body, headers })
        .then((r) => r.data);
  if (!publicRead) return request;
  // Share only concurrent reads (including StrictMode mounts), never cache results.
  const pending = request.finally(() => pendingPublicReads.delete(path));
  pendingPublicReads.set(path, pending);
  return pending;
}
export function errorText(error) {
  if (error.isAxiosError && !error.response)
    return "Die Verbindung zum Server ist gerade nicht verfügbar. Bitte erneut versuchen.";
  const detail = error.response?.data?.detail;
  if (Array.isArray(detail)) return detail.map((e) => e.msg).join(" · ");
  return (
    detail ||
    error.message ||
    "Das hat nicht geklappt. Bitte nochmals versuchen."
  );
}
export function loginUrl() {
  return (
    apiBase +
    "/auth/login?return_to=" +
    encodeURIComponent("/" + window.location.search)
  );
}

import React, { useEffect } from "react";

export default function LoginButton({ onLoginComplete = () => {} }) {
  const onLogin = () => {
    const api = (window.__API_BASE__ || "").toString().replace(/\/$/, "");
    const url = `${api}/auth/login`;
    const popup = window.open(url, "strava_oauth", "width=600,height=700");
    if (!popup) {
      window.location.href = url;
      return;
    }
    try {
      popup.focus();
    } catch (e) {}
  };

  useEffect(() => {
    function onMessage(e) {
      try {
        const data = e?.data;
        if (!data || typeof data !== "object") return;
        if (data.type === "strava_auth_complete") {
          if (data.success) {
            onLoginComplete(data.user || null);
          }
        }
      } catch (err) {
        // ignore malformed messages
      }
    }
    window.addEventListener("message", onMessage, false);
    return () => window.removeEventListener("message", onMessage, false);
  }, [onLoginComplete]);

  return (
    <button className="btn primary" onClick={onLogin} aria-label="Connect with Strava">
      Connect with Strava
    </button>
  );
}

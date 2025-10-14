import React from "react";

export default function LoginButton({ onLoginComplete = () => {} }) {
  // Öffne Backend-Login direkt (Backend leitet dann zu Strava weiter).
  const onLogin = () => {
    // öffne direkt das Backend (nicht die Frontend-URL)
    const url = "http://localhost:8000/auth/login";
    const popup = window.open(url, "strava_oauth", "width=600,height=700");
    if (!popup) {
      // Popup geblockt -> normale Navigation
      window.location.href = url;
      return;
    }

    // Polling: wenn Popup geschlossen wird, löse callback aus
    const checkInterval = 500;
    let elapsed = 0;
    const maxWait = 120000; // 2 Minuten fallback
    const timer = setInterval(() => {
      try {
        if (popup.closed) {
          clearInterval(timer);
          onLoginComplete();
        }
      } catch (e) {
        // cross-origin reads können fehlschlagen; ignorieren
      }
      elapsed += checkInterval;
      if (elapsed >= maxWait) {
        clearInterval(timer);
        try {
          popup.close();
        } catch {}
        onLoginComplete();
      }
    }, checkInterval);
  };

  return <button onClick={onLogin}>Mit Strava einloggen</button>;
}

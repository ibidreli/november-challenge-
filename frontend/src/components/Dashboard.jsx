import React, { useEffect, useState } from "react";
import axios from "axios";

export default function Dashboard({ refreshKey = 0 }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(false);

  // Backend base: prefer VITE_API_BASE_URL, otherwise known backend host.
  // Force HTTPS to avoid mixed-content errors.
  let backendBase = (import.meta.env.VITE_API_BASE_URL || "https://november-challenge.onrender.com")?.toString().trim() || "";
  if (!/^https?:\/\//i.test(backendBase)) backendBase = "https://" + backendBase;
  backendBase = backendBase.replace(/^http:\/\//i, "https://").replace(/\/$/, "");

  const load = async () => {
    setLoading(true);
    try {
      const u = await axios.get(`${backendBase}/users/me`, { timeout: 8000 }).then(r => r.data).catch(() => null);
      setUser(u && u.name ? u : null);
    } catch (err) {
      console.error("Dashboard load error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [refreshKey]);

  return (
    <div>
      <h2>Dashboard</h2>
      {loading && <div>Lädt…</div>}
      <div>
        <strong>Angemeldeter Benutzer:</strong>
        {user ? (
          <div>
            {user.name} — Score: {user.total_score ?? 0}
            <div style={{ marginTop: 12 }}>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(10, 1fr)", gap: 6, maxWidth: 560 }}>
                {(user.slots || new Array(30).fill(null)).map((s, idx) => (
                  <div key={idx} title={s ? `${s.km} km` : "frei"}
                       style={{
                         height: 28,
                         borderRadius: 4,
                         background: s ? "#38b5ae" : "#eee",
                         display: "flex",
                         alignItems: "center",
                         justifyContent: "center",
                         color: s ? "#fff" : "#666",
                         fontSize: 12,
                         fontWeight: 600
                       }}>
                    {s ? `${s.km} km` : idx+1}
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div>Kein Benutzer angemeldet (oder Backend nicht verbunden)</div>
        )}
      </div>
    </div>
  );
}

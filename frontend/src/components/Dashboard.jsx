import React, { useEffect, useState } from "react";
import axios from "axios";

export default function Dashboard({ refreshKey = 0 }) {
  const [user, setUser] = useState(null);
  const [leaderboard, setLeaderboard] = useState([]);
  const [loading, setLoading] = useState(false);

  // Backend base: prefer VITE_API_BASE_URL, otherwise known backend host.
  // Force HTTPS to avoid mixed-content errors.
  let backendBase = (import.meta.env.VITE_API_BASE_URL || "https://november-challenge.onrender.com")?.toString().trim() || "";
  if (!/^https?:\/\//i.test(backendBase)) backendBase = "https://" + backendBase;
  backendBase = backendBase.replace(/^http:\/\//i, "https://").replace(/\/$/, "");

  const load = async () => {
    setLoading(true);
    try {
      const [u, lb] = await Promise.all([
        axios.get(`${backendBase}/users/me`).then(r => r.data).catch(() => null),
        axios.get(`${backendBase}/users`).then(r => r.data).catch(() => [])
      ]);
      setUser(u && u.name ? u : null);
      setLeaderboard(Array.isArray(lb) ? lb : []);
    } catch (err) {
      console.error("Dashboard load error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [refreshKey]);

  // helper to compute km from slots (if frontend only)
  const kmFromSlots = (slots) => {
    if (!Array.isArray(slots)) return 0;
    return slots.reduce((sum, s) => sum + (s ? Number(s) : 0), 0);
  };

  // MiniGrid component (very small squares)
  const MiniGrid = ({ slots }) => {
    // normalize to length 30
    const arr = Array.isArray(slots) ? slots.slice(0,30).concat(Array(30 - Math.min(30, slots.length)).fill(null)) : Array(30).fill(null);
    return (
      <div className="mini-grid" aria-hidden="true">
        {arr.map((s, i) => (
          <div key={i} className={`mini-cell ${s ? "mini-filled" : "mini-empty"}`} />
        ))}
      </div>
    );
  };

  return (
    <div style={{ padding: 16 }}>
      <div style={{ display: "flex", gap: 16, alignItems: "center", justifyContent: "space-between", flexWrap: "wrap" }}>
        <div>
          <h1 style={{ margin: 0 }}>November Challenge</h1>
          <p style={{ margin: "6px 0 0", color: "#6b7280" }}>Persönliches Dashboard & Rangliste</p>
        </div>
        <div>
          {loading ? (
            <div style={{ color: "#666" }}>Lädt…</div>
          ) : user ? (
            <div style={{ textAlign: "right" }}>
              <div style={{ fontWeight: 700 }}>{user.name}</div>
              <div style={{ color: "#444" }}>Score: {user.total_score ?? 0}</div>
              <div style={{ color: "#444" }}>Monatliche km: {kmFromSlots(user.slots)}</div>
            </div>
          ) : (
            <div style={{ color: "#666" }}>Nicht verbunden — bitte Strava verbinden</div>
          )}
        </div>
      </div>

      <section style={{ marginTop: 20 }}>
        <h2 style={{ marginBottom: 8 }}>Rangliste</h2>
        {leaderboard.length === 0 ? (
          <div style={{ color: "#666" }}>Keine Teilnehmer gefunden.</div>
        ) : (
          <div style={{ display: "grid", gap: 8 }}>
            {leaderboard.map((p, idx) => (
              <div key={p.id} className="leader-row" style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: 10,
                background: idx < 3 ? "#fef3c7" : "#fff",
                borderRadius: 8,
                border: "1px solid #eee",
                boxShadow: "0 1px 4px rgba(10,10,10,0.03)"
              }}>
                <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
                  <div style={{
                    width: 36, height: 36, borderRadius: 8,
                    background: "#00b3a6", color: "#fff", display: "flex",
                    alignItems: "center", justifyContent: "center", fontWeight: 700
                  }}>
                    {String(p.name || "U").split(" ").map(n=>n[0]).join("").slice(0,2).toUpperCase()}
                  </div>
                  <div>
                    <div style={{ fontWeight: 700 }}>{p.name}</div>
                    <div style={{ fontSize: 13, color: "#666" }}>km: {p.km_total} • score: {p.total_score}</div>
                  </div>
                </div>

                <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
                  <MiniGrid slots={p.slots} />
                  <div style={{ fontWeight: 700, fontSize: 16 }}>{idx+1}</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

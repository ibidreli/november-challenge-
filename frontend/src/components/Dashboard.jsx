import React, { useEffect, useState } from "react";
import axios from "axios";
import Login from "../pages/Login"; // show login page inline when not authenticated

export default function Dashboard({ refreshKey = 0, onUserChange = () => {} }) {
  const [view, setView] = useState("personal"); // "personal" | "public"
  const [user, setUser] = useState(null);
  const [leaderboard, setLeaderboard] = useState([]);
  const [loading, setLoading] = useState(false);

  // backend base: prefer VITE_API_BASE_URL, otherwise known backend host.
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
      // normalize user: only accept if name exists
      const normalizedUser = (u && u.name) ? u : null;
      setUser(normalizedUser);

      // notify parent about current user (keeps header login button in sync)
      try { onUserChange(normalizedUser); } catch (e) {}

      // leaderboard fallback: if server returns empty but we have user, include user
      const lbArr = Array.isArray(lb) ? lb : [];
      if (lbArr.length === 0 && normalizedUser) {
        const slots = Array.isArray(normalizedUser.slots)
          ? normalizedUser.slots.map(s => (s && typeof s === "object" && "km" in s ? Number(s.km) : (typeof s === "number" ? Number(s) : null)))
          : [];
        lbArr.push({
          id: normalizedUser.id ?? 0,
          name: normalizedUser.name,
          total_score: normalizedUser.total_score ?? 0,
          km_total: slots.reduce((s, v) => s + (v ? v : 0), 0),
          slots: slots
        });
      }
      setLeaderboard(lbArr);
    } catch (err) {
      console.error("Dashboard load error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshKey]);

  // helpers
  const kmFromSlots = (slots) => {
    if (!Array.isArray(slots)) return 0;
    return slots.reduce((sum, s) => {
      if (!s) return sum;
      if (typeof s === "number") return sum + Number(s);
      if (typeof s === "object" && s.km != null) return sum + Number(s.km);
      return sum;
    }, 0);
  };

  // Personal grid: always show day number; show km when filled
  const PersonalGrid = ({ slots }) => {
    const arr = Array.isArray(slots) ? slots.slice(0,30).concat(Array(30 - Math.min(30, slots.length)).fill(null)) : Array(30).fill(null);
    return (
      <div className="personal-grid" aria-hidden="true">
        {arr.map((s, i) => {
          const filled = !!s;
          const km = filled ? (typeof s === "number" ? s : (s.km ?? "")) : null;
          return (
            <div key={i} className={`personal-cell ${filled ? "filled" : "empty"}`} title={filled ? `${km} km` : `Tag ${i+1}`}>
              <div className="cell-day">{i+1}</div>
              {filled ? <span className="cell-km">{km}</span> : null}
            </div>
          );
        })}
      </div>
    );
  };

  const MiniGrid = ({ slots }) => {
    const arr = Array.isArray(slots) ? slots.slice(0,30).concat(Array(30 - Math.min(30, slots.length)).fill(null)) : Array(30).fill(null);
    return (
      <div className="mini-grid" aria-hidden="true">
        {arr.map((s, i) => <div key={i} className={`mini-cell ${s ? "mini-filled" : "mini-empty"}`} />)}
      </div>
    );
  };

  // --- Render: no top title/tabs, show login page inline when not authenticated ---
  return (
    <div style={{ padding: 16 }}>
      {loading ? (
        <div style={{ color: "#666" }}>Lädt…</div>
      ) : !user ? (
        // show full login page inline (connect with Strava)
        <div>
          <h2>Bitte einloggen</h2>
          <Login />
          <p style={{ color: "#666", marginTop: 12 }}>Nach dem Verbinden erscheinen Deine persönlichen Statistiken hier.</p>
        </div>
      ) : (
        <div>
          {/* Personal summary */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
            <div>
              <div style={{ fontWeight: 700, fontSize: 18 }}>{user.name}</div>
              <div style={{ color: "#444", marginTop:6 }}>
                <span style={{ fontWeight:700 }}>Punkte: {user.total_score ?? kmFromSlots(user.slots)}</span>
                <span style={{ marginLeft:12, color:"#666" }}>Monatliche km: {kmFromSlots(user.slots)}</span>
              </div>
            </div>
          </div>

          <div style={{ marginTop: 12 }}>
            <PersonalGrid slots={user.slots} />
          </div>

          {/* Public leaderboard below */}
          <section style={{ marginTop: 20 }}>
            <h3 style={{ marginBottom: 8 }}>Öffentliche Rangliste</h3>
            {leaderboard.length === 0 ? (
              <div style={{ color: "#666" }}>Keine Teilnehmer gefunden.</div>
            ) : (
              <div style={{ display: "grid", gap: 8 }}>
                {leaderboard.map((p, idx) => (
                  <div key={p.id} style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: 10,
                    borderRadius: 8,
                    border: "1px solid #eee",
                    background: idx < 3 ? "#fffbeb" : "#fff"
                  }}>
                    <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
                      <div style={{
                        width: 36, height: 36, borderRadius: 8,
                        background: "#00b3a6", color: "#fff", display: "flex",
                        alignItems: "center", justifyContent: "center", fontWeight: 700
                      }}>
                        {String(p.name || "U").split(" ").map(n => n[0]).join("").slice(0,2).toUpperCase()}
                      </div>
                      <div>
                        <div style={{ fontWeight: 700 }}>{p.name}</div>
                        <div style={{ fontSize: 13, color: "#666" }}>km: {p.km_total} • punkte: {p.total_score}</div>
                      </div>
                    </div>

                    <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
                      <MiniGrid slots={p.slots} />
                      <div style={{ fontWeight: 700, fontSize: 16 }}>{idx + 1}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  );
}

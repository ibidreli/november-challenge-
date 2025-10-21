import React, { useEffect, useState } from "react";
import axios from "axios";

export default function Dashboard({ refreshKey = 0 }) {
  const [user, setUser] = useState(null);
  const [leaderboard, setLeaderboard] = useState([]);
  const [loading, setLoading] = useState(false);

  // backend base
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

      const lbArr = Array.isArray(lb) ? lb : [];
      // fallback: if no public users but user exists, show the user in leaderboard
      if (lbArr.length === 0 && u && u.name) {
        const slots = Array.isArray(u.slots) ? u.slots.map(s => (s && typeof s === "object" && "km" in s ? Number(s.km) : (typeof s === "number" ? Number(s) : null))) : [];
        lbArr.push({
          id: u.id ?? 0,
          name: u.name,
          total_score: u.total_score ?? 0,
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

  useEffect(() => { load(); }, [refreshKey]);

  const kmFromSlots = (slots) => {
    if (!Array.isArray(slots)) return 0;
    return slots.reduce((sum, s) => {
      if (!s) return sum;
      if (typeof s === "number") return sum + Number(s);
      if (typeof s === "object" && s.km != null) return sum + Number(s.km);
      return sum;
    }, 0);
  };

  const MiniGrid = ({ slots }) => {
    const arr = Array.isArray(slots) ? slots.slice(0,30).concat(Array(30 - Math.min(30, slots.length)).fill(null)) : Array(30).fill(null);
    return (
      <div className="mini-grid" aria-hidden="true">
        {arr.map((s, i) => <div key={i} className={`mini-cell ${s ? "mini-filled" : "mini-empty"}`} />)}
      </div>
    );
  };

  return (
    <div style={{ padding: 12 }}>
      <div className="dashboard-columns">
        {/* Left: Public leaderboard */}
        <div className="col-left">
          <h2 style={{ marginTop: 0, marginBottom: 8 }}>Öffentliche Rangliste</h2>
          {loading ? (
            <div style={{ color: "#666" }}>Lädt…</div>
          ) : leaderboard.length === 0 ? (
            <div style={{ color: "#666" }}>Keine Teilnehmer gefunden.</div>
          ) : (
            <div style={{ display: "grid", gap: 8 }}>
              {leaderboard.map((p, idx) => (
                <div key={p.id} className="leader-row" style={{
                  display:"flex", justifyContent:"space-between", alignItems:"center", padding:10, borderRadius:8, border:"1px solid #eee",
                  background: idx < 3 ? "#fffbeb" : "#fff"
                }}>
                  <div style={{ display:"flex", gap:12, alignItems:"center" }}>
                    <div style={{ width:36, height:36, borderRadius:8, background:"#00b3a6", color:"#fff", display:"flex", alignItems:"center", justifyContent:"center", fontWeight:700 }}>
                      {String(p.name||"U").split(" ").map(n=>n[0]).join("").slice(0,2).toUpperCase()}
                    </div>
                    <div>
                      <div style={{ fontWeight:700 }}>{p.name}</div>
                      <div style={{ fontSize:13, color:"#666" }}>Punkte: {p.total_score} • km: {p.km_total}</div>
                    </div>
                  </div>

                  <div style={{ display:"flex", gap:12, alignItems:"center" }}>
                    <MiniGrid slots={p.slots} />
                    <div style={{ fontWeight:700, fontSize:16 }}>{idx+1}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right: Personal panel */}
        <div className="col-right">
          <h2 style={{ marginTop: 0, marginBottom: 8 }}>Persönlich</h2>

          {loading ? (
            <div style={{ color:"#666" }}>Lädt…</div>
          ) : !user ? (
            <div className="panel-card" style={{ padding:12 }}>
              <div style={{ fontWeight:700, marginBottom:6 }}>Nicht angemeldet</div>
              <div style={{ color:"#666", marginBottom:10 }}>Du bist nicht verbunden oder wurdest noch nicht zum Challenge hinzugefügt.</div>
              <a className="btn primary" href={`${backendBase}/auth/login`}>Mit Strava verbinden</a>
            </div>
          ) : (
            <div className="panel-card" style={{ padding:12 }}>
              <div style={{ fontWeight:700, fontSize:18 }}>{user.name}</div>
              <div style={{ color:"#444", marginTop:6, marginBottom:8 }}>
                Punkte: <strong>{user.total_score ?? 0}</strong>
              </div>
              <div style={{ color:"#666", marginBottom:12 }}>Monatliche km: {kmFromSlots(user.slots)}</div>
              <div>
                {/* Personal 30-day grid with day numbers */}
                <div style={{ marginTop:6 }}>
                  <div className="personal-grid">
                    {Array.from({length:30}, (_,i) => {
                      const s = Array.isArray(user.slots) ? user.slots[i] : null;
                      const filled = !!s;
                      const km = filled ? (typeof s === "number" ? s : (s.km ?? "")) : null;
                      return (
                        <div key={i} className={`personal-cell ${filled ? "filled" : "empty"}`} title={filled ? `${km} km` : `Tag ${i+1}`}>
                          <div className="cell-day">{i+1}</div>
                          {filled ? <div className="cell-km">{km}</div> : null}
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

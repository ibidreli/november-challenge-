import React, { useEffect, useState } from "react";
import axios from "axios";

export default function Dashboard({ refreshKey = 0 }) {
  const [view, setView] = useState("personal"); // "personal" | "public"
  const [user, setUser] = useState(null);
  const [leaderboard, setLeaderboard] = useState([]);
  const [loading, setLoading] = useState(false);

  // backend base: prefer VITE_API_BASE_URL at build time, else fallback to known host
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

      // ensure leaderboard is an array; if empty but we have user, add user as fallback
      const lbArr = Array.isArray(lb) ? lb : [];
      if (lbArr.length === 0 && u && u.name) {
        // transform user into leaderboard shape
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

  useEffect(() => {
    load();
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

  return (
    <div className="simple-dashboard" style={{ padding: 16 }}>
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", gap:16, flexWrap:"wrap" }}>
        <div>
          <h1 style={{ margin:0 }}>November Challenge</h1>
        </div>

        <div style={{ display:"flex", gap:10, alignItems:"center" }}>
          <div className="tabs" role="tablist" aria-label="View selector">
            <button className={`tab ${view==="personal" ? "active" : ""}`} onClick={() => setView("personal")}>Deine Leistungen</button>
            <button className={`tab ${view==="public" ? "active" : ""}`} onClick={() => setView("public")}>Rangliste</button>
          </div>
          {/* single Login button in header already present; keep this small helper to refresh after login */}
        </div>
      </div>

      <div style={{ marginTop: 18 }}>
        {view === "personal" && (
          <div>
            <h2 style={{ marginTop:0 }}>Meine Übersicht</h2>
            {loading ? (
              <div style={{ color:"#666" }}>Lädt…</div>
            ) : !user ? (
              <div style={{ display:"flex", gap:12, alignItems:"center" }}>
                <div style={{ flex:1 }}>
                  <p>Du bist nicht angemeldet. Bitte mit Strava verbinden, um deinen persönlichen Fortschritt zu sehen.</p>
                </div>
                <div>
                  <a className="btn primary" href={`${backendBase}/auth/login`}>Connect with Strava</a>
                </div>
              </div>
            ) : (
              <div>
                <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", gap:12, flexWrap:"wrap" }}>
                  <div>
                    <div style={{ fontWeight:700 }}>{user.name}</div>
                    <div style={{ color:"#444" }}>Punkte: {user.total_score ?? 0}</div>
                    <div style={{ color:"#444" }}>Monatliche Kilometer: {kmFromSlots(user.slots)}</div>
                  </div>
                </div>

                <div style={{ marginTop:12 }}>
                  <PersonalGrid slots={user.slots} />
                </div>
              </div>
            )}
          </div>
        )}

        {view === "public" && (
          <div>
            <h2 style={{ marginTop:0 }}>Öffentliche Rangliste</h2>
            {loading ? (
              <div style={{ color:"#666" }}>Lädt…</div>
            ) : leaderboard.length === 0 ? (
              <div style={{ color:"#666" }}>Keine Teilnehmer gefunden.</div>
            ) : (
              <div style={{ display:"grid", gap:8 }}>
                {leaderboard.map((p, idx) => (
                  <div key={p.id} className="leader-row" style={{
                    display:"flex", justifyContent:"space-between", alignItems:"center", padding:10, borderRadius:8, border:"1px solid #eee", background: idx<3 ? "#fffbeb" : "#fff"
                  }}>
                    <div style={{ display:"flex", gap:12, alignItems:"center" }}>
                      <div style={{ width:36, height:36, borderRadius:8, background:"#00b3a6", color:"#fff", display:"flex", alignItems:"center", justifyContent:"center", fontWeight:700 }}>
                        {String(p.name||"U").split(" ").map(n=>n[0]).join("").slice(0,2).toUpperCase()}
                      </div>
                      <div>
                        <div style={{ fontWeight:700 }}>{p.name}</div>
                        <div style={{ fontSize:13, color:"#666" }}>km: {p.km_total} • score: {p.total_score}</div>
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
        )}
      </div>
    </div>
  );
}

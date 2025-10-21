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

  // --- small UI components inside this file (keeps repo small) ---
  const UserSummaryCard = ({ user }) => {
    const initials = (user && user.name) ? user.name.split(" ").map(n=>n[0]).join("").slice(0,2).toUpperCase() : "NA";
    return (
      <div className="ucard">
        <div className="ucard-left">
          <div className="avatar-large">{initials}</div>
        </div>
        <div className="ucard-right">
          <h3>{user.name}</h3>
          <div className="meta">
            <div><strong>{user.total_score ?? 0}</strong> points</div>
            <div style={{marginLeft: 12}}><strong>{(user.slots||[]).reduce((s,slot)=>s + (slot && slot.km ? slot.km : 0), 0)}</strong> km</div>
          </div>
          <div style={{marginTop:8}}>
            <button className="btn small">View activities</button>
          </div>
        </div>
      </div>
    );
  };

  // MonthGrid: 30 tiles for the challenge month
  const MonthGrid = ({ user }) => {
    const slots = (user && user.slots) ? user.slots : new Array(30).fill(null);
    const days = Array.from({length: 30}, (_,i) => i+1);
    return (
      <div className="month-grid">
        {days.map(day => {
          const slot = slots[day-1];
          const has = !!slot;
          const km = has ? slot.km : null;
          const longRun = km && km >= 10;
          return (
            <div key={day} className={`day-tile ${has ? "active" : ""} ${longRun ? "long" : ""}`} title={has ? `${km} km` : `Day ${day}`}>
              <div className="day-number">{day}</div>
              {has && <div className="km-pill">{km} km</div>}
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className="dashboard-root">
      <div className="dashboard-top">
        <div className="title-block">
          <h2>November Challenge</h2>
          <p className="muted">Your monthly progress and slots overview</p>
        </div>
        <div className="user-block">
          {loading && <div>Loading…</div>}
          {!loading && user && <UserSummaryCard user={user} />}
          {!loading && !user && <div className="no-user">Kein Benutzer angemeldet — bitte mit Strava verbinden.</div>}
        </div>
      </div>

      <div className="dashboard-body">
        <div className="left-panel">
          <div className="panel-card">
            <h4>Participant</h4>
            {user ? (
              <div style={{display:"flex", alignItems:"center", gap:12}}>
                <div className="avatar">{(user.name||"").split(" ").map(n=>n[0]).join("").slice(0,2).toUpperCase()}</div>
                <div>
                  <div style={{fontWeight:700}}>{user.name}</div>
                  <div className="muted">Score: {user.total_score ?? 0}</div>
                </div>
              </div>
            ) : (
              <div className="muted">No participant data</div>
            )}
            <div style={{marginTop:12}}>
              <button className="btn">Leaderboard</button>
              <button className="btn ghost" style={{marginLeft:8}}>Export CSV</button>
            </div>
          </div>
        </div>

        <div className="right-panel">
          <div className="panel-card">
            <h4>Month Overview</h4>
            <MonthGrid user={user} />
            <div className="legend" style={{marginTop:10}}>
              <span className="legend-item"><span className="legend-swatch"></span> No activity</span>
              <span className="legend-item"><span className="legend-swatch active"></span> Run</span>
              <span className="legend-item"><span className="legend-swatch long"></span> Long run (≥10 km)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

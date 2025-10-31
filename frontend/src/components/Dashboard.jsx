import React, { useEffect, useState } from "react";
import axios from "axios";

axios.defaults.withCredentials = true;

export default function Dashboard({ refreshKey = 0 }) {
  const [view, setView] = useState("personal"); // "personal" | "public"
  const [user, setUser] = useState(null);
  const [leaderboard, setLeaderboard] = useState([]);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [u, lb] = await Promise.all([
        axios
          .get("/users/me")
          .then((r) => r.data)
          .catch((e) => {
            console.warn("GET /users/me failed", e);
            return null;
          }),
        // Cache-Busting für die Rangliste -> immer frisch beim Reload
        axios
          .get("/users/", { withCredentials: false, params: { t: Date.now() } })
          .then((r) => r.data)
          .catch((e) => {
            console.warn("GET /users/ failed", e);
            return [];
          }),
      ]);

      setUser(u && u.name ? u : null);

      const lbArr = Array.isArray(lb) ? lb : [];
      // Fallback: Wenn öffentliches LB leer ist, aber User vorhanden,
      // zeige wenigstens dessen Slots/Score an.
      if (lbArr.length === 0 && u && u.name) {
        const slots = Array.isArray(u.slots)
          ? u.slots.map((s) =>
              s && typeof s === "object" && "km" in s
                ? Number(s.km)
                : typeof s === "number"
                ? Number(s)
                : null
            )
          : [];
        lbArr.push({
          id: u.id ?? 0,
          name: u.name,
          total_score: u.total_score ?? 0,
          km_total: slots.reduce((s, v) => s + (v ? v : 0), 0),
          slots: slots,
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

  const kmFromSlots = (slots) => {
    if (!Array.isArray(slots)) return 0;
    return slots.reduce((sum, s) => {
      if (!s) return sum;
      if (typeof s === "number") return sum + Number(s);
      if (typeof s === "object" && s.km != null) return sum + Number(s.km);
      return sum;
    }, 0);
  };

  // Anzahl Tage mit >0 km
  const daysFromSlots = (slots) => {
    if (!Array.isArray(slots)) return 0;
    return slots.reduce((n, s) => {
      if (!s) return n;
      if (typeof s === "number") return s > 0 ? n + 1 : n;
      if (typeof s === "object") {
        const km = Number(s.km ?? 0);
        return km > 0 ? n + 1 : n;
      }
      return n;
    }, 0);
  };

  const PersonalGrid = ({ slots }) => {
    const arr = Array.isArray(slots)
      ? slots
          .slice(0, 30)
          .concat(Array(30 - Math.min(30, slots.length)).fill(null))
      : Array(30).fill(null);
    return (
      <div className="personal-grid" aria-hidden="true">
        {arr.map((s, i) => {
          const filled = !!s;
          const km = filled
            ? typeof s === "number"
              ? s
              : s.km ?? ""
            : null;
          return (
            <div
              key={i}
              className={`personal-cell ${filled ? "filled" : "empty"}`}
              title={filled ? `${km} km` : `Tag ${i + 1}`}
            >
              <div className="cell-day">{i + 1}</div>
            </div>
          );
        })}
      </div>
    );
  };

  const MiniGrid = ({ slots }) => {
    const arr = Array.isArray(slots)
      ? slots
          .slice(0, 30)
          .concat(Array(30 - Math.min(30, slots.length)).fill(null))
      : Array(30).fill(null);
    return (
      <div className="mini-grid" aria-hidden="true">
        {arr.map((s, i) => (
          <div
            key={i}
            className={`mini-cell ${s ? "mini-filled" : "mini-empty"}`}
          />
        ))}
      </div>
    );
  };

  // Calculate total km from all players
  const totalKmAll = leaderboard.reduce((sum, p) => sum + kmFromSlots(p.slots), 0);

  return (
    <div className="simple-dashboard" style={{ padding: 16 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 16,
          flexWrap: "wrap",
        }}
      >
        <div>
          <h1 style={{ margin: 0 }}>November Challenge</h1>
        </div>

        <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap", justifyContent: "flex-end" }}>
          <div className="tabs" role="tablist" aria-label="View selector">
            <button
              className={`tab ${view === "personal" ? "active" : ""}`}
              onClick={() => setView("personal")}
            >
              Übersicht
            </button>
            <button
              className={`tab ${view === "public" ? "active" : ""}`}
              onClick={() => setView("public")}
            >
              Rangliste
            </button>
          </div>
          
          <div style={{
            background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
            color: "white",
            padding: "8px 14px",
            borderRadius: "8px",
            fontWeight: "700",
            fontSize: "14px",
            whiteSpace: "nowrap",
            boxShadow: "0 2px 8px rgba(102, 126, 234, 0.3)"
          }}>
            ✓ Zusammen: {totalKmAll} km
          </div>
        </div>
      </div>

      <div style={{ marginTop: 18 }}>
        {view === "personal" && (
          <div>
            <h2 style={{ marginTop: 0 }}>Übersicht</h2>
            {loading ? (
              <div style={{ color: "#666" }}>Lädt…</div>
            ) : !user ? (
              <div className="not-logged">
                <div className="not-logged-text">
                  <p>
                    Du bist nicht angemeldet. Bitte mit Strava verbinden, um
                    deine persönliche Übersicht zu sehen.
                  </p>
                </div>
                <div className="not-logged-action">
                  <a
                    className="btn primary"
                    href={`${
                      window.__API_BASE__ || axios.defaults.baseURL
                    }/auth/login`}
                  >
                    Connect with Strava
                  </a>
                </div>
              </div>
            ) : (
              <div>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    gap: 12,
                    flexWrap: "wrap",
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 700 }}>{user.name}</div>
                    <div style={{ color: "#444" }}>
                      Tage: {daysFromSlots(user.slots)}
                    </div>
                    <div style={{ color: "#444" }}>
                      Km: {kmFromSlots(user.slots)}
                    </div>
                  </div>
                </div>

                <div style={{ marginTop: 12 }}>
                  <PersonalGrid slots={user.slots} />
                </div>
              </div>
            )}
          </div>
        )}

        {view === "public" && (
          <div>
            <h2 style={{ marginTop: 0 }}>Rangliste</h2>
            {loading ? (
              <div style={{ color: "#666" }}>Lädt…</div>
            ) : leaderboard.length === 0 ? (
              <div style={{ color: "#666" }}>Keine Teilnehmer gefunden.</div>
            ) : (
              <div style={{ display: "grid", gap: 8 }}>
                {leaderboard.map((p, idx) => (
                  <div
                    key={p.id ?? `${p.name}-${idx}`}
                    className="leader-row"
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      padding: 10,
                      borderRadius: 8,
                      border: "1px solid #eee",
                      background: idx < 3 ? "#fffbeb" : "#fff",
                    }}
                  >
                    <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
                      <div
                        style={{
                          width: 36,
                          height: 36,
                          borderRadius: 8,
                          background: "#00b3a6",
                          color: "#fff",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          fontWeight: 700,
                        }}
                      >
                        {String(p.name || "U")
                          .split(" ")
                          .map((n) => n[0])
                          .join("")
                          .slice(0, 2)
                          .toUpperCase()}
                      </div>
                      <div>
                        <div style={{ fontWeight: 700 }}>{p.name}</div>
                        <div style={{ fontSize: 13, color: "#666" }}>
                          <div>Tage: {daysFromSlots(p.slots)}</div>
                          <div>Km: {p.total_score}</div>
                        </div>
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
          </div>
        )}
      </div>
    </div>
  );
}

import React, { useEffect, useState } from "react";
import axios from "axios";

export default function Dashboard({ refreshKey = 0, onProcessed = () => {} }) {
  const [user, setUser] = useState(null);
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [u, a] = await Promise.all([
        axios.get("/users/me").then(r => r.data).catch(() => null),
        axios.get("/activities").then(r => r.data).catch(() => []),
      ]);
      setUser(u && u.name ? u : null);
      setActivities(Array.isArray(a) ? a : []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [refreshKey]);

  const processActivity = async (id) => {
    try {
      const res = await axios.post(`/activities/process/${id}`);
      alert(JSON.stringify(res.data));
      onProcessed();
    } catch (err) {
      console.error(err);
      alert("Fehler beim Verarbeiten der Aktivität.");
    }
  };

  return (
    <div>
      <h2>Dashboard</h2>
      {loading && <div>Lädt…</div>}
      <div>
        <strong>Angemeldeter Benutzer:</strong>
        {user ? (
          <div>
            {user.name} — Score: {user.total_score ?? 0}
            {/* 30 Felder anzeigen */}
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

      <h3>Aktivitäten</h3>
      {activities.length === 0 ? (
        <div>Keine Aktivitäten gefunden.</div>
      ) : (
        <table>
          <thead>
            <tr><th>ID</th><th>Datum</th><th>Distanz (km)</th><th>Status</th><th>Aktion</th></tr>
          </thead>
          <tbody>
            {activities.map(a => (
              <tr key={a.id}>
                <td>{a.id}</td>
                <td>{a.date}</td>
                <td>{a.distance_km}</td>
                <td>{a.status}</td>
                <td>
                  <button onClick={() => processActivity(a.id)} disabled={a.status === "claimed"}>
                    Process
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

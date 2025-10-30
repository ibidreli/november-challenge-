import React, { useEffect, useState } from "react";
import axios from "axios";
import Dashboard from "./components/Dashboard";
import logo from "../logo/Logo.png"; // import logo from frontend/logo/Logo.png

export default function App() {
  const [refreshKey, setRefreshKey] = useState(0);
  const [syncing, setSyncing] = useState(false);

  // Beim App-Start/Reload: alle Nutzer/Activities synchronisieren (Server holt neu von Strava)
  useEffect(() => {
    let cancelled = false;

    async function initialSync() {
      try {
        setSyncing(true);
        await axios.post("/users/sync_all", null, { withCredentials: true });
      } catch (e) {
        console.warn("Initial sync_all failed:", e);
      } finally {
        if (!cancelled) {
          setSyncing(false);
          setRefreshKey((k) => k + 1); // Dashboard nach Sync neu laden
        }
      }
    }

    initialSync();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div>
      <header className="header">
        <div className="header-left">
          <img src={logo} alt="November Challenge" className="logo" />
          <div className="app-title">
            <div className="title-main">November Challenge</div>
            <div className="title-sub">Monatliche Running Challenge</div>
          </div>
        </div>
      </header>

      <main className="container" style={{ marginTop: 20 }}>
        {syncing && (
          <div style={{ marginBottom: 8, color: "#666", fontSize: 14 }}>
            Aktualisiere Aktivitäten
          </div>
        )}
        <Dashboard refreshKey={refreshKey} />
      </main>
    </div>
  );
}

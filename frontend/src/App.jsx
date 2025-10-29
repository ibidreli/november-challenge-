import React, { useEffect, useState } from "react";
import axios from "axios";
import Dashboard from "./components/Dashboard";
import logo from "../logo/Logo.png"; // import logo from frontend/logo/Logo.png

export default function App() {
  const [refreshKey, setRefreshKey] = useState(0);
  const [syncing, setSyncing] = useState(false);

  // Beim App-Start: alle Nutzer/Activities synchronisieren (Backend zieht via Strava)
  useEffect(() => {
    let cancelled = false;

    async function initialSync() {
      try {
        setSyncing(true);
        // Server-seitiger Sync: zieht für alle Nutzer die neuesten Aktivitäten
        await axios.post("/users/sync_all", null, { withCredentials: true });
      } catch (e) {
        // unkritisch — UI lädt trotzdem
        console.warn("Initial sync_all failed:", e);
      } finally {
        if (!cancelled) {
          setSyncing(false);
          // Dashboard neu laden (damit Rangliste & persönliche Ansicht aktuell sind)
          setRefreshKey((k) => k + 1);
        }
      }
    }

    initialSync();

    return () => {
      cancelled = true;
    };
  }, []);

  // Optional: wenn der Tab wieder sichtbar wird, kurz neu synchronisieren & refreshen
  useEffect(() => {
    let running = false;

    async function syncOnFocus() {
      if (document.visibilityState !== "visible" || running) return;
      running = true;
      try {
        await axios.post("/users/sync_all", null, { withCredentials: true });
      } catch (e) {
        // ok
      } finally {
        setRefreshKey((k) => k + 1);
        running = false;
      }
    }

    document.addEventListener("visibilitychange", syncOnFocus);
    return () => document.removeEventListener("visibilitychange", syncOnFocus);
  }, []);

  return (
    <div>
      <header className="header">
        <div className="header-left">
          <img src={logo} alt="November Challenge" className="logo" />
          <div className="app-title">
            <div className="title-main">November Challenge</div>
            <div className="title-sub">Monthly running challenge</div>
          </div>
        </div>
        <nav className="header-nav">
          <a>Dashboard</a> {/* keep only Dashboard nav */}
        </nav>
        {/* header-right removed to avoid duplicate Connect button */}
      </header>

      <main className="container" style={{ marginTop: 20 }}>
        {syncing && (
          <div style={{ marginBottom: 8, color: "#666", fontSize: 14 }}>
            Aktualisiere Aktivitäten…
          </div>
        )}
        <Dashboard refreshKey={refreshKey} />
      </main>
    </div>
  );
}

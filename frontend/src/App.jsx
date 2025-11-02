import React, { useEffect, useState } from "react";
import axios from "axios";
import Dashboard from "./components/Dashboard";
import AdminPanel from "./components/AdminPanel";
import logo from "../logo/Logo.png";

export default function App() {
  const [refreshKey, setRefreshKey] = useState(0);
  const [syncing, setSyncing] = useState(false);
  const [currentPage, setCurrentPage] = useState(() => {
    const path = window.location.pathname;
    const hash = window.location.hash;
    const isAdmin = (path && path.includes("/admin")) || (hash && hash.includes("/admin"));
    return isAdmin ? "admin" : "dashboard";
  });

  useEffect(() => {
    const path = window.location.pathname;
    const hash = window.location.hash;
    const isAdmin = (path && path.includes("/admin")) || (hash && hash.includes("/admin"));
    if (isAdmin) {
      setCurrentPage("admin");
    }
  }, []);

  // ⚠️ ENTFERNT: Nicht bei jedem Reload synchen!
  // Stattdessen: Background-Task auf dem Backend macht Auto-Sync alle 30 Min
  // Frontend lädt nur Daten, triggert keinen Strava-Sync beim Reload

  return (
    <div>
      <header className="header">
        <div className="header-left">
          <img src={logo} alt="November Jogging Challenge" className="logo" />
          <div className="app-title">
            <div className="title-main">November Jogging Challenge</div>
            <div className="title-sub">Monatliche Jogging Challenge</div>
          </div>
        </div>
      </header>

      <main className="container" style={{ marginTop: 20 }}>
        {syncing && (
          <div style={{ marginBottom: 0, color: "#666", fontSize: 0 }}>
            
          </div>
        )}
        {currentPage === "admin" ? (
          <AdminPanel />
        ) : (
          <Dashboard refreshKey={refreshKey} />
        )}
      </main>
    </div>
  );
}

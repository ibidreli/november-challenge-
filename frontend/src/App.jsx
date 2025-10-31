import React, { useEffect, useState } from "react";
import axios from "axios";
import Dashboard from "./components/Dashboard";
import AdminPanel from "./components/AdminPanel";
import logo from "../logo/Logo.png"; // import logo from frontend/logo/Logo.png

export default function App() {
  const [refreshKey, setRefreshKey] = useState(0);
  const [syncing, setSyncing] = useState(false);
  const [currentPage, setCurrentPage] = useState(() => {
    // Check URL on initial render - try both pathname and hash
    const path = window.location.pathname;
    const hash = window.location.hash;
    console.log("Initial pathname:", path, "hash:", hash); // Debug
    
    // Prüfe pathname ODER hash für /admin
    const isAdmin = (path && path.includes("/admin")) || (hash && hash.includes("/admin"));
    return isAdmin ? "admin" : "dashboard";
  });

  // Check URL for admin page on mount
  useEffect(() => {
    const path = window.location.pathname;
    const hash = window.location.hash;
    console.log("Pathname in effect:", path, "hash:", hash); // Debug
    
    const isAdmin = (path && path.includes("/admin")) || (hash && hash.includes("/admin"));
    if (isAdmin) {
      setCurrentPage("admin");
    }
  }, []);

  // Beim App-Start/Reload: alle Nutzer/Activities synchronisieren (Server holt neu von Strava)
  useEffect(() => {
    let cancelled = false;

    async function initialSync() {
      // Only sync if on dashboard page
      if (currentPage !== "admin") {
        try {
          setSyncing(true);
          await axios.post("/users/sync_all", null, { withCredentials: false });
        } catch (e) {
          console.warn("Initial sync_all failed:", e);
        } finally {
          if (!cancelled) {
            setSyncing(false);
            setRefreshKey((k) => k + 1); // Dashboard nach Sync neu laden
          }
        }
      }
    }

    initialSync();
    return () => {
      cancelled = true;
    };
  }, [currentPage]);

  // Admin page - skip dashboard rendering
  if (currentPage === "admin") {
    return <AdminPanel />;
  }

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
        <Dashboard refreshKey={refreshKey} />
      </main>
    </div>
  );
}

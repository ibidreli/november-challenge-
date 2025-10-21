import React, { useState } from "react";
import Dashboard from "./components/Dashboard";
import logo from "../logo/Logo.png"; // import logo from frontend/logo/Logo.png

export default function App() {
  const [refreshKey, setRefreshKey] = useState(0);

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
        <Dashboard refreshKey={refreshKey} />
      </main>
    </div>
  );
}

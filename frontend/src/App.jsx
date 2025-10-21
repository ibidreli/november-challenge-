import React, { useState } from "react";
import LoginButton from "./components/LoginButton";
import Dashboard from "./components/Dashboard";

export default function App() {
  const [refreshKey, setRefreshKey] = useState(0);
  const logo = "/logo.png"; // ensure logo.png is served from project root or public/

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
          <a>Dashboard</a>
          <a>Training</a>
          <a>Maps</a>
          <a>Support</a>
        </nav>
        <div className="header-right">
          <LoginButton onLoginComplete={() => setRefreshKey(k => k + 1)} />
        </div>
      </header>

      <main className="container" style={{marginTop:20}}>
        <Dashboard refreshKey={refreshKey} />
      </main>
    </div>
  );
}

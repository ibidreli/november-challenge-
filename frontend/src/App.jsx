import React, { useState } from "react";
import LoginButton from "./components/LoginButton";
import Dashboard from "./components/Dashboard";
import logo from "../logo/Logo.png"; // import logo from frontend/logo/Logo.png

export default function App() {
  const [refreshKey, setRefreshKey] = useState(0);
  const [currentUser, setCurrentUser] = useState(null);

  // called by LoginButton when OAuth finished (receives user object)
  const handleLoginComplete = (user) => {
    // store user and trigger dashboard refresh
    setCurrentUser(user || null);
    setRefreshKey((k) => k + 1);
  };

  // Called by Dashboard when it loads the current user (keeps header state consistent)
  const handleUserChange = (user) => {
    setCurrentUser(user || null);
  };

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
        <div className="header-right">
          {/* only show login button when not logged in */}
          {!currentUser && (
            <LoginButton onLoginComplete={handleLoginComplete} />
          )}
        </div>
      </header>

      <main className="container" style={{ marginTop: 20 }}>
        <Dashboard
          refreshKey={refreshKey}
          onUserChange={handleUserChange}
        />
      </main>
    </div>
  );
}

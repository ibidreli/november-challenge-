import React, { useState } from "react";
import LoginButton from "./components/LoginButton";
import Dashboard from "./components/Dashboard";

export default function App() {
  const [refreshKey, setRefreshKey] = useState(0);
  return (
    <div className="container">
      <h1>November Challenge — Demo</h1>
      <p>Kurzdemo: Login via Strava, Aktivitäten sehen und verarbeiten.</p>
      {/* Übergib Callback, damit LoginButton nach Login das Dashboard neu laden kann */}
      <LoginButton onLoginComplete={() => setRefreshKey(k => k + 1)} />
      <hr />
      <Dashboard refreshKey={refreshKey} onProcessed={() => setRefreshKey(k => k + 1)} />
    </div>
  );
}

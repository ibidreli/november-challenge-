import React, { useCallback, useEffect, useState } from "react";
import Dashboard from "./components/Dashboard";
import AdminPanel from "./components/AdminPanel";
import { api, isPreview, loginUrl, errorText } from "./api";
import { previewLogin } from "./previewData";
import logo from "../logo/Logo.png";

export default function App() {
  const [user, setUser] = useState(null),
    [authLoading, setAuthLoading] = useState(true);
  const [error, setError] = useState(""),
    [version, setVersion] = useState(0);
  const admin = window.location.pathname.replace(/\/$/, "") === "/admin";
  const refresh = useCallback(async () => {
    try {
      setUser(await api("/users/me"));
      setError("");
    } catch (e) {
      if (e.response?.status === 401) {
        setUser(null);
        setError("");
      } else setError(errorText(e));
    } finally {
      setAuthLoading(false);
      setVersion((v) => v + 1);
    }
  }, []);
  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, 60000);
    window.addEventListener("focus", refresh);
    return () => {
      clearInterval(timer);
      window.removeEventListener("focus", refresh);
    };
  }, [refresh]);
  async function logout() {
    try {
      await api("/auth/logout", { method: "POST" });
      setUser(null);
      setError("");
      setVersion((v) => v + 1);
    } catch (e) {
      setError(errorText(e));
    }
  }
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Zum Inhalt
      </a>
      <header className="header">
        <a href="/" className="brand">
          <img src={logo} alt="" className="logo" />
          <div>
            <strong>November Jogging Challenge</strong>
            <span>Gemeinsam durch den November</span>
          </div>
        </a>
        <div className="account">
          {authLoading ? (
            <span className="muted">Anmeldung prüfen …</span>
          ) : user ? (
            <>
              <span className="account-name">{user.name}</span>
              <button className="btn small" onClick={logout}>
                Abmelden
              </button>
            </>
          ) : (
            <a
              className="btn strava"
              href={isPreview ? "#" : loginUrl()}
              onClick={
                isPreview
                  ? (e) => {
                      e.preventDefault();
                      previewLogin(true);
                      refresh();
                    }
                  : undefined
              }
            >
              Mit Strava anmelden <span aria-hidden="true">↗</span>
            </a>
          )}
        </div>
      </header>
      {isPreview && (
        <div className="preview-banner">
          Vorschau mit Beispieldaten · Änderungen werden nicht gespeichert.
        </div>
      )}
      <main id="main" className="container">
        {error && (
          <div role="alert" className="notice error">
            {error}{" "}
            <button onClick={refresh} className="text-button">
              Erneut versuchen
            </button>
          </div>
        )}
        {new URLSearchParams(location.search).has("auth_error") && (
          <div className="notice">
            Die Strava-Anmeldung wurde nicht abgeschlossen. Du kannst sie oben
            erneut starten.
          </div>
        )}
        {admin ? (
          <AdminPanel />
        ) : (
          <Dashboard
            user={user}
            version={version}
            refresh={refresh}
            authLoading={authLoading}
          />
        )}
      </main>
      <footer>
        November Challenge · Gemeinsam zählt jeder Lauf.{" "}
        <a href={admin ? "/" : "/admin"}>{admin ? "Zur Challenge" : "Admin"}</a>
      </footer>
    </div>
  );
}

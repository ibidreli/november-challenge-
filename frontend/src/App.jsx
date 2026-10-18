import React, {
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import Dashboard from "./components/Dashboard";
import RunnerLoader from "./components/RunnerLoader";
import { api, isPreview, loginUrl, errorText } from "./api";
import { previewLogin } from "./previewData";
import logo from "../logo/Logo.png";
const AdminPanel = lazy(() => import("./components/AdminPanel"));
const About = lazy(() => import("./components/About"));

const readPath = () => window.location.pathname.replace(/\/$/, "");

export default function App() {
  const [user, setUser] = useState(null),
    [authLoading, setAuthLoading] = useState(true);
  const [error, setError] = useState(""),
    [version, setVersion] = useState(0);
  const [path, setPath] = useState(readPath);
  const admin = path === "/admin",
    about = path === "/about";
  const returnTab = new URLSearchParams(location.search).get("from");
  const returnTo = ["ranking", "groups"].includes(returnTab)
    ? `/?tab=${returnTab}`
    : "/";
  useEffect(() => {
    const updatePath = () => setPath(readPath());
    window.addEventListener("popstate", updatePath);
    return () => window.removeEventListener("popstate", updatePath);
  }, []);
  function navigate(event, destination) {
    if (
      event.button !== 0 ||
      event.metaKey ||
      event.ctrlKey ||
      event.shiftKey ||
      event.altKey
    )
      return;
    event.preventDefault();
    history.pushState({}, "", destination);
    window.dispatchEvent(new PopStateEvent("popstate"));
    window.scrollTo(0, 0);
  }
  function toggleAbout(event) {
    if (about) {
      navigate(event, returnTo);
      return;
    }
    const tab = new URLSearchParams(location.search).get("tab");
    navigate(
      event,
      ["ranking", "groups"].includes(tab) ? `/about?from=${tab}` : "/about",
    );
  }
  const pendingRefresh = useRef(null),
    didRefresh = useRef(false);
  const refresh = useCallback(() => {
    if (pendingRefresh.current) return pendingRefresh.current;
    pendingRefresh.current = (async () => {
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
        if (didRefresh.current) setVersion((v) => v + 1);
        didRefresh.current = true;
        pendingRefresh.current = null;
      }
    })();
    return pendingRefresh.current;
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
        <a href="/" className="brand" onClick={(event) => navigate(event, "/")}>
          <img src={logo} alt="" className="logo" />
          <div>
            <strong>November Jogging Challenge</strong>
            <span>Gemeinsam durch den November</span>
          </div>
        </a>
        <div className="header-actions">
          <a
            className={`info-link${about ? " active" : ""}`}
            href={about ? returnTo : "/about"}
            aria-label={about ? "Zurück zur Challenge" : "Über uns"}
            title={about ? "Zurück zur Challenge" : "Über uns"}
            onClick={toggleAbout}
          >
            <svg
              viewBox="0 0 24 24"
              width="26"
              height="26"
              fill="none"
              aria-hidden="true"
            >
              <circle
                cx="12"
                cy="12"
                r="9"
                stroke="currentColor"
                strokeWidth="1.8"
              />
              <path
                d="M12 11v6"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
              />
              <circle cx="12" cy="7.5" r="1.1" fill="currentColor" />
            </svg>
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
                Mit Strava anmelden
              </a>
            )}
          </div>
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
        {about ? (
          <Suspense fallback={<RunnerLoader />}>
            <About returnTo={returnTo} navigate={navigate} />
          </Suspense>
        ) : admin ? (
          <Suspense fallback={<RunnerLoader />}>
            <AdminPanel />
          </Suspense>
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
        November Challenge · Made by Elias Pulver.{" "}
        <a href={admin ? "/" : "/admin"}>{admin ? "Zur Challenge" : "Admin"}</a>
      </footer>
    </div>
  );
}

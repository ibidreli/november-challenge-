import React, { lazy, Suspense, useEffect, useState } from "react";
import { api, errorText, loginUrl } from "../api";
import ChallengeProgress from "./ChallengeProgress";
import ChallengeStats from "./ChallengeStats";
import Leaderboard from "./Leaderboard";
import usePublicResource from "../usePublicResource";
import TestNotice from "./TestNotice";
import RunnerLoader from "./RunnerLoader";
import { WHATSAPP_INVITE_URL } from "./WhatsAppNotice";
import { challengeDate } from "../time";
const Groups = lazy(() => import("./Groups"));

export default function Dashboard({ user, version, refresh, authLoading }) {
  const readTab = () => {
    const value = new URLSearchParams(location.search).get("tab");
    return ["ranking", "groups"].includes(value) ? value : "overview";
  };
  const [tab, setTab] = useState(readTab),
    [error, setError] = useState(""),
    [retry, setRetry] = useState(0),
    [syncing, setSyncing] = useState(false);
  const publicVersion = `${version}:${retry}`;
  const config = usePublicResource("/challenge", publicVersion);
  const stats = usePublicResource(
    "/challenge/statistics",
    publicVersion,
    tab === "overview",
  );
  const people = usePublicResource("/users/", publicVersion, tab === "ranking");
  const data = config.data ? { config: config.data, stats: stats.data } : null;
  const loadError =
    error ||
    (tab === "ranking"
      ? people.error
      : tab === "overview"
        ? config.error || stats.error
        : "");
  useEffect(() => {
    const handler = () => setTab(readTab());
    window.addEventListener("popstate", handler);
    return () => window.removeEventListener("popstate", handler);
  }, []);
  function changeTab(value) {
    setTab(value);
    const url = new URL(location);
    value === "overview"
      ? url.searchParams.delete("tab")
      : url.searchParams.set("tab", value);
    history.pushState({}, "", url);
  }
  async function sync() {
    setSyncing(true);
    try {
      await api("/users/me/sync", { method: "POST" });
      setTimeout(refresh, 5000);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setSyncing(false);
    }
  }
  const current = data?.config.periods.find((p) => p.current),
    open =
      user?.cells.filter((c) => c.status === "open").map((c) => c.km) || [];
  return (
    <div className="dashboard">
      <div className="page-heading">
        <div>
          <span className="eyebrow">
            {data
              ? `${data.config.year} · ${challengeDate(data.config.starts_on || data.config.periods[0].starts_on)}–${challengeDate(data.config.finale_date)}`
              : "November Challenge"}
          </span>
          <h1>November Challenge</h1>
        </div>
        <nav className="tabs" aria-label="Hauptnavigation">
          {[
            ["overview", "Übersicht"],
            ["ranking", "Rangliste"],
            ["groups", "Laufgruppen"],
          ].map(([key, label]) => (
            <button
              key={key}
              className={tab === key ? "active" : ""}
              aria-current={tab === key ? "page" : undefined}
              onClick={() => changeTab(key)}
            >
              {label}
            </button>
          ))}
        </nav>
      </div>
      <TestNotice config={data?.config} />
      {loadError && (
        <div className="notice error" role="alert">
          {loadError}{" "}
          <button
            className="text-button"
            onClick={() => {
              setError("");
              setRetry((value) => value + 1);
            }}
          >
            Erneut laden
          </button>
        </div>
      )}
      {tab === "groups" ? (
        <Suspense fallback={<RunnerLoader />}>
          <Groups user={user} />
        </Suspense>
      ) : tab === "ranking" ? (
        people.data ? (
          <Leaderboard
            people={people.data}
            total={people.data.reduce(
              (sum, person) => sum + person.total_score,
              0,
            )}
          />
        ) : (
          !people.error && <RunnerLoader />
        )
      ) : !data || authLoading ? (
        !config.error && <RunnerLoader />
      ) : (
        <>
          {user && (
            <section
              className="personal-panel"
              aria-labelledby="personal-title"
            >
              <div className="section-heading">
                <div>
                  <span className="eyebrow">Deine Challenge</span>
                  <h2 id="personal-title">Hallo {user.name.split(" ")[0]}</h2>
                </div>
                <div className="personal-totals">
                  <strong>
                    {user.completed_count}
                    <small>/30</small>
                  </strong>
                  <span>
                    Distanzen · <b>{user.total_score} km</b>
                  </span>
                </div>
              </div>
              <div className="week-focus">
                <span className="week-badge">
                  {current
                    ? `Woche ${current.number}`
                    : data.config.server_date === data.config.finale_date
                      ? "Abschlusslauf"
                      : "Dein nächster Schritt"}
                </span>
                <div>
                  {current ? (
                    current.published ? (
                      open.length ? (
                        <>
                          <strong>
                            Noch offen:{" "}
                            {open.map((km) => `${km} km`).join(" · ")}
                          </strong>
                          <span>
                            Bis{" "}
                            {new Date(
                              current.ends_on + "T12:00",
                            ).toLocaleDateString("de-CH", {
                              day: "numeric",
                              month: "numeric",
                            })}{" "}
                            · Reihenfolge frei wählbar
                          </span>
                        </>
                      ) : (
                        <strong>
                          Alle Distanzen dieser Woche erledigt. Gut gelaufen!
                        </strong>
                      )
                    ) : (
                      <>
                        <strong>
                          Die Distanzen dieser Woche werden bald veröffentlicht.
                        </strong>
                        <span>
                          Auslosung am{" "}
                          {new Date(
                            current.draw_on + "T12:00",
                          ).toLocaleDateString("de-CH")}
                        </span>
                      </>
                    )
                  ) : (
                    <>
                      <strong>
                        {data.config.server_date <
                        (data.config.starts_on ||
                          data.config.periods[0].starts_on)
                          ? `Am ${challengeDate(data.config.starts_on || data.config.periods[0].starts_on, true)} startet die Challenge.`
                          : data.config.server_date === data.config.finale_date
                            ? `Heute: mindestens ${data.config.finale_km} km für den Abschlusslauf.`
                            : "Hier siehst du deinen Fortschritt für die ganze Challenge."}
                      </strong>
                      <span>
                        ★ {data.config.finale_km} km sind für den gemeinsamen
                        Abschluss am {challengeDate(data.config.finale_date)}{" "}
                        reserviert.
                      </span>
                    </>
                  )}
                </div>
              </div>
              <ChallengeProgress cells={user.cells} />
              <details className="rules">
                <summary>So zählt dein Lauf</summary>
                <p>
                  Pro Tag zählt dein längster einzelner Lauf. Dabei wird die
                  grösste noch offene Distanz der aktuellen Woche abgehakt, die
                  du mit diesem Lauf erreicht oder übertroffen hast. Du
                  entscheidest selbst, in welcher Reihenfolge du die Distanzen
                  läufst. Mehrere Läufe werden nicht zusammengerechnet. Offene
                  Distanzen verfallen am Ende des jeweiligen Zeitraums.
                </p>
                <p>
                  Am {challengeDate(data.config.finale_date)} zählt ein Lauf mit
                  mindestens {data.config.finale_km} km automatisch für den
                  Abschluss. Falls du probleme mit der Synchronisation hast,
                  wende dich bitte an das Organisatonsteam, direkt bei WhatsApp.
                </p>
              </details>
              <div className="sync-line">
                <span className="muted">
                  {user.last_synced_at
                    ? `Letzte Synchronisation: ${new Date(user.last_synced_at).toLocaleString("de-CH", { day: "numeric", month: "numeric", hour: "2-digit", minute: "2-digit", timeZone: "Europe/Zurich" })}`
                    : "Deine Strava-Läufe werden im Hintergrund geladen."}
                </span>
                <button
                  className="text-button"
                  disabled={syncing}
                  onClick={sync}
                >
                  {syncing ? "Wird gestartet …" : "Strava synchronisieren"}
                </button>
              </div>
              {!user.strava_connected && (
                <p className="notice">
                  Die Strava-Verbindung muss erneuert werden.{" "}
                  <a href={loginUrl()}>Strava erneut verbinden</a>.
                </p>
              )}
              {user.sync_error && (
                <p className="notice" role="status">
                  {user.sync_error}
                </p>
              )}
            </section>
          )}
          {!user && !authLoading && (
            <section className="intro">
              <div>
                <span className="eyebrow">
                  {data.config.test_mode
                    ? "30 Distanzen. Dein Testlauf."
                    : "30 Distanzen."}
                </span>
                <h2>Ein Monat, viele gemeinsame Schritte.</h2>
                <p>
                  Jede Woche werden neue Distanzen ausgelost. Du entscheidest,
                  an welchem Tag du welche läufst. Melde dich oben mit Strava
                  an, dann erscheint hier deine persönliche Übersicht.
                </p>
                <p className="intro-whatsapp">
                  Die Kommunikation zur Challenge läuft über{" "}
                  <a
                    href={WHATSAPP_INVITE_URL}
                    target="_blank"
                    rel="noopener noreferrer"
                    title="WhatsApp öffnen (neuer Tab)"
                  >
                    WhatsApp
                  </a>
                  .
                </p>
              </div>
              <ol>
                <li>
                  <b>Auslosung abwarten</b>
                  <span>Jeweils 8 / 7 / 7 / 7 Distanzen pro Woche.</span>
                </li>
                <li>
                  <b>Eine Distanz pro Tag erledigen</b>
                  <span>
                    Dein längster Lauf zählt automatisch. Die grösste noch
                    offene Distanz der aktuellen Woche wird abgehakt.
                  </span>
                </li>
                <li>
                  <b>Gemeinsam abschliessen</b>
                  <span>
                    Wir werden die Challenge am{" "}
                    {challengeDate(data.config.finale_date)} wenn möglich
                    Gemeinsam abschliessen, mit einer Strecke von{" "}
                    {data.config.finale_km} km. Schön bist du dabei!
                  </span>
                </li>
              </ol>
            </section>
          )}
          {data.stats ? (
            <ChallengeStats stats={data.stats} config={data.config} />
          ) : (
            !stats.error && <RunnerLoader />
          )}
          <details className="rules schedule">
            <summary>Auslosungen und Zeiträume</summary>
            <div className="period-list">
              {data.config.periods.map((p) => (
                <div key={p.number}>
                  <strong>
                    Woche {p.number} · {p.capacity} Distanzen
                  </strong>
                  <span>
                    {new Date(p.starts_on + "T12:00").toLocaleDateString(
                      "de-CH",
                    )}{" "}
                    –{" "}
                    {new Date(p.ends_on + "T12:00").toLocaleDateString("de-CH")}
                  </span>
                  <span>
                    {p.published
                      ? p.distances.map((n) => `${n} km`).join(" · ")
                      : `Auslosung am ${new Date(p.draw_on + "T12:00").toLocaleDateString("de-CH")}`}
                  </span>
                </div>
              ))}
            </div>
          </details>
          {user && (
            <p className="overview-whatsapp">
              Die Kommunikation zur Challenge läuft über{" "}
              <a
                href={WHATSAPP_INVITE_URL}
                target="_blank"
                rel="noopener noreferrer"
                title="WhatsApp öffnen (neuer Tab)"
              >
                WhatsApp
              </a>
              .
            </p>
          )}
        </>
      )}
    </div>
  );
}

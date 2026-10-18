import React, { useEffect, useState } from "react";
import { api, errorText, isPreview } from "../api";
import { localInput, runDate, challengeDate } from "../time";
import TestNotice from "./TestNotice";

function DrawEditor({ period, onSave, onReset, busy, finale }) {
  const [value, setValue] = useState(period.draft_distances.join(", "));
  useEffect(
    () => setValue(period.draft_distances.join(", ")),
    [period.draft_distances],
  );
  function save(publish) {
    const distances = value
      .trim()
      .split(/[\s,;]+/)
      .filter(Boolean)
      .map(Number);
    onSave(period.number, distances, publish);
  }
  return (
    <article className="draw-card">
      <div className="section-heading">
        <h3>Woche {period.number}</h3>
        <span className={`badge${period.published ? "" : " neutral"}`}>
          {period.published ? "Veröffentlicht" : "Entwurf"}
        </span>
      </div>
      <p>
        {new Date(period.starts_on + "T12:00").toLocaleDateString("de-CH")} –{" "}
        {new Date(period.ends_on + "T12:00").toLocaleDateString("de-CH")}
      </p>
      <p className="muted">
        Auslosung:{" "}
        {new Date(period.draw_on + "T12:00").toLocaleDateString("de-CH")} ·{" "}
        {period.capacity} Distanzen
      </p>
      <label>
        Ausgeloste Distanzen in km
        <input
          disabled={!period.editable || busy}
          value={value}
          placeholder={
            period.capacity === 8
              ? "5, 6, 9, 14, 19, 24, 27, 29"
              : "7 Distanzen, mit Kommas getrennt"
          }
          onChange={(e) => setValue(e.target.value)}
        />
      </label>
      <p className="muted">
        Genau {period.capacity} verschiedene Zahlen von 1–30; {finale} km
        bleiben für den Abschluss reserviert.
      </p>
      {period.editable ? (
        <div className="form-actions">
          <button className="btn" disabled={busy} onClick={() => save(false)}>
            Entwurf speichern
          </button>
          <button
            className="btn primary"
            disabled={busy}
            onClick={() => save(true)}
          >
            Veröffentlichen
          </button>
        </div>
      ) : (
        <p className="muted">Seit Beginn des Zeitraums gesperrt.</p>
      )}
      {(period.published || period.draft_distances.length > 0) && (
        <button
          className="text-button danger"
          disabled={busy}
          onClick={() => {
            if (
              window.confirm(
                `Auslosung für Woche ${period.number} zurücksetzen? Die Distanzen werden freigegeben und die Wertungen dieser Woche entfernt. Gespeicherte Läufe bleiben erhalten und werden nach einer erneuten Veröffentlichung neu gewertet.`,
              )
            )
              onReset(period.number);
          }}
        >
          Auslosung zurücksetzen
        </button>
      )}
    </article>
  );
}

export default function AdminPanel() {
  const [token, setToken] = useState(localStorage.getItem("nc_admin") || ""),
    [password, setPassword] = useState("");
  const [tab, setTab] = useState("challenge"),
    [data, setData] = useState(null),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false);
  const [finale, setFinale] = useState(15),
    [newName, setNewName] = useState("");
  const [activity, setActivity] = useState({
    user_id: "",
    date: localInput(Date.now()).slice(0, 10),
    distance_km: "",
  });
  async function load() {
    const [config, users, activities, groups] = await Promise.all(
      [
        "/admin/challenge",
        "/admin/users",
        "/admin/activities",
        "/admin/community",
      ].map((path) => api(path, { admin: true })),
    );
    setData({ config, users, activities, groups });
    setFinale(config.finale_km);
  }
  function failure(e) {
    setError(errorText(e));
    if (e.response?.status === 401) {
      localStorage.removeItem("nc_admin");
      setToken("");
    }
  }
  useEffect(() => {
    if (token) load().catch(failure);
  }, [token]);
  async function login(e) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await api("/admin/login", {
        method: "POST",
        body: { password },
      });
      localStorage.setItem("nc_admin", result.token);
      setToken(result.token);
      setPassword("");
    } catch (e) {
      failure(e);
    } finally {
      setBusy(false);
    }
  }
  async function mutate(path, method, body, message) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await api(path, { method, body, admin: true });
      await load();
      setNotice(message || "Gespeichert.");
    } catch (e) {
      failure(e);
    } finally {
      setBusy(false);
    }
  }
  async function logout() {
    try {
      await api("/admin/logout", { method: "POST", admin: true });
    } catch {}
    localStorage.removeItem("nc_admin");
    setToken("");
    setData(null);
  }
  const used = new Set([
    data?.config.finale_km,
    ...(data?.config.periods.flatMap((p) => p.draft_distances) || []),
  ]);
  const remaining = Array.from({ length: 30 }, (_, i) => i + 1).filter(
    (km) => !used.has(km),
  );
  return (
    <div className="admin-panel">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Organisation</span>
          <h1>Admin</h1>
        </div>
        {token && (
          <button className="btn small" onClick={logout}>
            Admin abmelden
          </button>
        )}
      </div>
      <TestNotice config={data?.config} />
      {error && (
        <p role="alert" className="notice error">
          {error}
        </p>
      )}
      {notice && (
        <p role="status" className="notice success">
          {notice}
        </p>
      )}
      {!token ? (
        <form onSubmit={login} className="admin-login">
          <p>
            Hier verwaltest du Auslosungen, Abschlussdistanz und manuelle
            Korrekturen.
          </p>
          <label>
            Admin-Passwort
            <input
              type="password"
              required
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          <button disabled={busy} className="btn primary">
            {busy ? "Anmelden …" : "Anmelden"}
          </button>
        </form>
      ) : (
        <>
          <nav className="tabs admin-tabs" aria-label="Admin-Bereiche">
            {[
              ["challenge", "Challenge"],
              ["users", "Teilnehmer"],
              ["activities", "Aktivitäten"],
              ["groups", "Läufergruppen"],
            ].map(([key, title]) => (
              <button
                key={key}
                className={tab === key ? "active" : ""}
                onClick={() => setTab(key)}
              >
                {title}
              </button>
            ))}
          </nav>
          {!data ? (
            <p className="empty-state">Administration wird geladen …</p>
          ) : tab === "challenge" ? (
            <>
              <h2>Challenge {data.config.year}</h2>
              <p>
                Trage die Ergebnisse eurer Auslosung ein. Entwürfe sieht nur der
                Admin; mit «Veröffentlichen» erscheinen die Distanzen für alle.
                Nach Beginn einer veröffentlichten Woche ist diese gesperrt. Mit
                «Auslosung zurücksetzen» kannst du die Distanzen auch danach neu
                eintragen und veröffentlichen.
              </p>
              <form
                className="finale-form"
                onSubmit={(e) => {
                  e.preventDefault();
                  mutate(
                    "/admin/challenge/finale",
                    "PUT",
                    { km: Number(finale) },
                    "Abschlussdistanz gespeichert.",
                  );
                }}
              >
                <label>
                  Abschlusslauf am {challengeDate(data.config.finale_date)} ·
                  Distanz in km
                  <input
                    type="number"
                    min="1"
                    max="30"
                    step="1"
                    required
                    value={finale}
                    onChange={(e) => setFinale(e.target.value)}
                  />
                </label>
                <button className="btn" disabled={busy}>
                  Abschlussdistanz speichern
                </button>
              </form>
              <div className="pot">
                <strong>Noch im Topf: {remaining.length} Distanzen</strong>
                <p>
                  {remaining.length
                    ? remaining.map((km) => `${km} km`).join(" · ")
                    : "Alle Distanzen sind verteilt."}
                </p>
                <small>
                  Gespeicherte Entwürfe und die Abschlussdistanz sind bereits
                  reserviert.
                </small>
              </div>
              <div className="draw-grid">
                {data.config.periods.map((p) => (
                  <DrawEditor
                    key={p.number}
                    period={p}
                    finale={data.config.finale_km}
                    busy={busy}
                    onReset={(n) =>
                      mutate(
                        `/admin/challenge/periods/${n}`,
                        "DELETE",
                        undefined,
                        "Auslosung zurückgesetzt. Distanzen sind wieder frei; gespeicherte Läufe bleiben erhalten.",
                      )
                    }
                    onSave={(n, distances, publish) =>
                      mutate(
                        `/admin/challenge/periods/${n}${publish ? "/publish" : ""}`,
                        publish ? "POST" : "PUT",
                        { distances },
                        publish
                          ? "Auslosung veröffentlicht und vorhandene Läufe neu gewertet."
                          : "Entwurf gespeichert; öffentlich noch nicht sichtbar.",
                      )
                    }
                  />
                ))}
              </div>
            </>
          ) : tab === "users" ? (
            <>
              <h2>Teilnehmer verwalten</h2>
              <form
                className="inline-form"
                onSubmit={(e) => {
                  e.preventDefault();
                  mutate(
                    "/admin/users",
                    "POST",
                    { name: newName },
                    "Teilnehmer hinzugefügt.",
                  );
                  setNewName("");
                }}
              >
                <label>
                  Teilnehmer ohne Strava hinzufügen
                  <input
                    required
                    maxLength="100"
                    placeholder="Vorname Nachname"
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                  />
                </label>
                <button className="btn primary" disabled={busy}>
                  Hinzufügen
                </button>
              </form>
              <div className="admin-list">
                {data.users.map((u) => (
                  <article key={u.id}>
                    <div>
                      <strong>{u.name}</strong>
                      <span>
                        {u.total_score} km · {u.completed_count}/30 ·{" "}
                        {u.strava_id ? "Strava verbunden" : "Manuell"}
                      </span>
                    </div>
                    <div className="actions">
                      <button
                        className="btn small"
                        onClick={() => {
                          const name = window.prompt("Anzeigename", u.name);
                          if (name?.trim())
                            mutate(`/admin/users/${u.id}`, "PUT", { name });
                        }}
                      >
                        Name ändern
                      </button>
                      <button
                        className="text-button danger"
                        onClick={() => {
                          if (
                            window.confirm(
                              `${u.name} und alle zugehörigen Aktivitäten und Resultate dauerhaft löschen?`,
                            )
                          )
                            mutate(`/admin/users/${u.id}`, "DELETE");
                        }}
                      >
                        Löschen
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            </>
          ) : tab === "activities" ? (
            <>
              <div className="section-heading">
                <h2>Aktivitäten und Korrekturen</h2>
                <button
                  className="btn small"
                  disabled={busy}
                  onClick={() =>
                    mutate(
                      "/admin/sync",
                      "POST",
                      undefined,
                      "Strava-Synchronisation im Hintergrund gestartet. Ergebnisse erscheinen nach dem Neuladen.",
                    )
                  }
                >
                  Strava abrufen
                </button>
              </div>
              <p className="notice">
                Eine manuelle Tageskorrektur ersetzt die Strava-Wertung dieses
                Tages. Beim Löschen der Korrektur zählt wieder der längste
                Strava-Lauf. Die Wochenwertung wird sofort neu berechnet.
              </p>
              <form
                className="form-grid activity-form"
                onSubmit={(e) => {
                  e.preventDefault();
                  mutate(
                    "/admin/activities",
                    "POST",
                    {
                      user_id: Number(activity.user_id),
                      date: activity.date,
                      distance_km: Number(activity.distance_km),
                    },
                    "Tageskorrektur gespeichert und Wertung aktualisiert.",
                  );
                }}
              >
                <label>
                  Teilnehmer
                  <select
                    required
                    value={activity.user_id}
                    onChange={(e) =>
                      setActivity({ ...activity, user_id: e.target.value })
                    }
                  >
                    <option value="">Bitte wählen</option>
                    {data.users.map((u) => (
                      <option key={u.id} value={u.id}>
                        {u.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Laufdatum
                  <input
                    required
                    type="date"
                    min={
                      data.config.starts_on || data.config.periods[0].starts_on
                    }
                    max={
                      isPreview
                        ? data.config.finale_date
                        : [
                            data.config.finale_date,
                            localInput(Date.now()).slice(0, 10),
                          ].sort()[0]
                    }
                    value={activity.date}
                    onChange={(e) =>
                      setActivity({ ...activity, date: e.target.value })
                    }
                  />
                </label>
                <label>
                  Tatsächlich gelaufene km
                  <input
                    required
                    type="number"
                    min="0.001"
                    max="300"
                    step="0.001"
                    value={activity.distance_km}
                    onChange={(e) =>
                      setActivity({ ...activity, distance_km: e.target.value })
                    }
                  />
                </label>
                <button className="btn primary" disabled={busy}>
                  Korrektur speichern
                </button>
              </form>
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Teilnehmer</th>
                      <th>Datum</th>
                      <th>Gelaufen</th>
                      <th>Gewertet</th>
                      <th>Status</th>
                      <th>Aktion</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.activities.map((a) => (
                      <tr key={a.id}>
                        <td>
                          {data.users.find((u) => u.id === a.user_id)?.name ||
                            a.user_id}
                        </td>
                        <td>{a.date}</td>
                        <td>{a.distance_km} km</td>
                        <td>{a.effective_km || 0} km</td>
                        <td>
                          {a.is_manual ? "Manuell · " : "Strava · "}
                          {{
                            claimed: "gewertet",
                            too_short: "zu kurz",
                            daily_not_selected: "anderer Tageslauf zählt",
                            waiting_draw: "wartet auf Auslosung",
                            period_complete: "Woche erledigt",
                            deleted: "in Strava gelöscht",
                            admin_excluded: "ausgeschlossen",
                            not_run: "kein Lauf",
                            pending: "offen",
                          }[a.status] || a.status}
                        </td>
                        <td>
                          {a.status === "admin_excluded" ? (
                            <button
                              className="text-button"
                              disabled={busy}
                              onClick={() =>
                                mutate(
                                  `/admin/activities/${a.id}/restore`,
                                  "POST",
                                  undefined,
                                  "Aktivität wieder in der Wertung.",
                                )
                              }
                            >
                              Wieder werten
                            </button>
                          ) : (
                            <button
                              className="text-button danger"
                              onClick={() => {
                                if (
                                  window.confirm(
                                    "Diese Aktivität von der Wertung ausschliessen?",
                                  )
                                )
                                  mutate(`/admin/activities/${a.id}`, "DELETE");
                              }}
                            >
                              Ausschliessen
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="muted">
                Die letzten 1000 Aktivitäten werden angezeigt. Strava-Läufe
                bitte in Strava ändern; Korrekturen hier über die manuelle
                Eingabe erfassen.
              </p>
            </>
          ) : (
            <>
              <h2>Läufergruppen moderieren</h2>
              <div className="admin-list">
                {data.groups.map((r) => (
                  <article key={r.id}>
                    <div>
                      <strong>{r.name}</strong>
                      <span>
                        {runDate(
                          r.starts_at + (r.starts_at.endsWith("Z") ? "" : "Z"),
                        )}{" "}
                        · {r.meeting_point}
                      </span>
                    </div>
                    <button
                      className="text-button danger"
                      onClick={() => {
                        if (window.confirm("Diesen gemeinsamen Lauf absagen?"))
                          mutate(`/admin/community/${r.id}`, "DELETE");
                      }}
                    >
                      Absagen
                    </button>
                  </article>
                ))}
              </div>
              {!data.groups.length && (
                <p className="empty-state">Aktuell keine Läufe geplant.</p>
              )}
            </>
          )}
          <button
            className="text-button admin-reload"
            onClick={() => load().catch(failure)}
          >
            Daten neu laden
          </button>
        </>
      )}
    </div>
  );
}

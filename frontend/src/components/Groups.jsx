import React, { useCallback, useEffect, useMemo, useState } from "react";
import { api, errorText } from "../api";
import { localInput, zurichToISO, runDate, pace } from "../time";
import StartMap from "./StartMap";
import Modal from "./Modal";

function RunForm({ user, run, onSaved, onClose }) {
  const [name, setName] = useState(run?.creator_name || user?.name || ""),
    [distance, setDistance] = useState(run?.distance_km || ""),
    [speed, setSpeed] = useState(pace(run?.pace_seconds || 360));
  const [time, setTime] = useState(run ? localInput(run.starts_at) : ""),
    [place, setPlace] = useState(run?.meeting_point || "");
  const [point, setPoint] = useState(
      run ? { latitude: run.latitude, longitude: run.longitude } : null,
    ),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function submit(e) {
    e.preventDefault();
    setError("");
    if (!point) {
      setError("Bitte den Startpunkt auf der Karte auswählen.");
      return;
    }
    if (!/^\d{1,2}:[0-5]\d$/.test(speed)) {
      setError("Bitte die Pace als min:sek eingeben, zum Beispiel 6:00.");
      return;
    }
    const [m, s] = speed.split(":").map(Number);
    if (m * 60 + s < 60 || m * 60 + s > 1800) {
      setError("Bitte eine Pace zwischen 1:00 und 30:00 min/km wählen.");
      return;
    }
    setBusy(true);
    try {
      await api(run ? `/community/${run.id}` : "/community", {
        method: run ? "PUT" : "POST",
        body: {
          name,
          distance_km: Number(distance),
          pace_seconds: m * 60 + s,
          starts_at: zurichToISO(time),
          meeting_point: place,
          ...point,
        },
      });
      onSaved();
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal
      title={run ? "Lauf bearbeiten" : "Gemeinsam laufen"}
      onClose={onClose}
    >
      <p className="muted">
        Alle können mitmachen – auch ohne Strava. Die Startzeit gilt für die
        Schweiz.
      </p>
      <form onSubmit={submit}>
        <div className="form-grid">
          <label>
            Dein Name
            <input
              required
              maxLength="60"
              autoComplete="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </label>
          <label>
            Distanz in km
            <input
              required
              type="number"
              min="0.1"
              max="300"
              step="0.1"
              inputMode="decimal"
              placeholder="9"
              value={distance}
              onChange={(e) => setDistance(e.target.value)}
            />
          </label>
          <label>
            Voraussichtliche Pace <span className="muted">min/km</span>
            <input
              required
              inputMode="text"
              placeholder="6:00"
              value={speed}
              onChange={(e) => setSpeed(e.target.value)}
            />
          </label>
          <label>
            Tag und Startzeit <span className="muted">Schweiz</span>
            <input
              required
              type="datetime-local"
              min={localInput(Date.now() + 60000)}
              value={time}
              onChange={(e) => setTime(e.target.value)}
            />
          </label>
        </div>
        <label className="map-label">
          Startpunkt auf der Karte auswählen{" "}
          <span className="muted">Antippen oder die Kartenmitte setzen</span>
        </label>
        <StartMap point={point} onChange={setPoint} />
        <p className="muted" aria-live="polite">
          {point
            ? `Startpunkt gewählt: ${point.latitude.toFixed(5)}, ${point.longitude.toFixed(5)}`
            : "Noch kein Startpunkt gewählt."}
        </p>
        <label>
          Treffpunkt kurz beschreiben
          <input
            required
            maxLength="160"
            placeholder="Zum Beispiel: beim Brunnen vor dem Bahnhof"
            value={place}
            onChange={(e) => setPlace(e.target.value)}
          />
        </label>
        {error && (
          <p role="alert" className="notice error">
            {error}
          </p>
        )}
        <p className="muted">
          Der Lauf verschwindet 3 Stunden nach dem Start. Als Ersteller bist du
          automatisch dabei.
        </p>
        <div className="form-actions">
          <button type="button" className="btn" onClick={onClose}>
            Abbrechen
          </button>
          <button disabled={busy} className="btn primary">
            {busy ? "Speichern …" : "Lauf speichern"}
          </button>
        </div>
      </form>
    </Modal>
  );
}

export default function Groups({ user }) {
  const [runs, setRuns] = useState([]),
    [loading, setLoading] = useState(true),
    [error, setError] = useState("");
  const [form, setForm] = useState(null),
    [joining, setJoining] = useState(null),
    [name, setName] = useState(user?.name || ""),
    [busy, setBusy] = useState(false),
    [focusId, setFocusId] = useState(null);
  const [clockOffset, setClockOffset] = useState(0),
    [tick, setTick] = useState(Date.now());
  const load = useCallback(async () => {
    try {
      const data = await api("/community");
      setRuns(data.runs);
      setClockOffset(new Date(data.server_now).getTime() - Date.now());
      setError("");
    } catch (e) {
      setError(errorText(e));
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    load();
    const poll = setInterval(load, 60000),
      timer = setInterval(() => setTick(Date.now()), 1000);
    window.addEventListener("focus", load);
    return () => {
      clearInterval(poll);
      clearInterval(timer);
      window.removeEventListener("focus", load);
    };
  }, [load]);
  useEffect(() => {
    if (user?.name) setName(user.name);
  }, [user?.name]);
  const closeForm = useCallback(() => setForm(null), []),
    closeJoin = useCallback(() => setJoining(null), []);
  const expired = runs
    .filter((r) => new Date(r.expires_at).getTime() <= tick + clockOffset)
    .map((r) => r.id)
    .join(",");
  const active = useMemo(
    () => runs.filter((r) => !expired.split(",").includes(r.id)),
    [runs, expired],
  );
  async function action(path, method, body) {
    setBusy(true);
    try {
      await api(path, { method, body });
      setJoining(null);
      await load();
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  function select(id) {
    setFocusId(id);
    document
      .getElementById(`run-${id}`)
      ?.scrollIntoView({ behavior: "smooth", block: "center" });
  }
  return (
    <section aria-labelledby="groups-title">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Zusammen läuft’s leichter</span>
          <h2 id="groups-title">Läufergruppen</h2>
        </div>
        <button className="btn primary" onClick={() => setForm("new")}>
          <span aria-hidden="true">＋</span> Lauf erstellen
        </button>
      </div>
      <p className="muted">
        Finde einen Lauf in deiner Nähe oder lade andere ein. Erstellen und
        Teilnehmen geht auch ohne Anmeldung.
      </p>
      {error && (
        <p className="notice error" role="alert">
          {error}{" "}
          <button className="text-button" onClick={load}>
            Erneut laden
          </button>
        </p>
      )}
      <StartMap runs={active} onSelect={select} focusId={focusId} />
      {loading ? (
        <p className="empty-state">Läufe werden geladen …</p>
      ) : !active.length ? (
        <div className="empty-state">
          <strong>Noch kein gemeinsamer Lauf geplant.</strong>
          <p>Erstelle den ersten und setze einen Treffpunkt auf der Karte.</p>
          <button className="btn" onClick={() => setForm("new")}>
            ＋ Lauf erstellen
          </button>
        </div>
      ) : (
        <div className="group-grid">
          {active.map((r) => (
            <article
              id={`run-${r.id}`}
              key={r.id}
              className={`group-card${focusId === r.id ? " selected" : ""}`}
            >
              <div className="group-date">{runDate(r.starts_at)}</div>
              <div className="section-heading">
                <h3>{r.distance_km} km gemeinsam laufen</h3>
                {r.joined && <span className="badge">Du bist dabei</span>}
              </div>
              <p className="group-pace">
                {pace(r.pace_seconds)} <span>min/km · voraussichtlich</span>
              </p>
              <button
                className="text-button place-link"
                onClick={() => {
                  setFocusId(r.id);
                  document
                    .querySelector(".map-canvas")
                    ?.scrollIntoView({ behavior: "smooth", block: "center" });
                }}
              >
                ⌖ {r.meeting_point}
              </button>
              <div className="participants">
                <strong>
                  {r.participants.length}{" "}
                  {r.participants.length === 1 ? "Person ist" : "Personen sind"}{" "}
                  dabei
                </strong>
                <p>{r.participants.join(" · ")}</p>
              </div>
              <div className="group-actions">
                {!r.joined && (
                  <button
                    className="btn primary"
                    disabled={busy}
                    onClick={() => {
                      setName(user?.name || name);
                      setJoining(r);
                    }}
                  >
                    Teilnehmen
                  </button>
                )}
                {r.can_leave && (
                  <button
                    className="btn"
                    disabled={busy}
                    onClick={() =>
                      action(`/community/${r.id}/participants/me`, "DELETE")
                    }
                  >
                    Nicht mehr teilnehmen
                  </button>
                )}
                {r.can_manage && (
                  <>
                    <button
                      className="btn"
                      onClick={() => setForm(r)}
                      disabled={
                        new Date(r.starts_at).getTime() <= tick + clockOffset
                      }
                    >
                      Bearbeiten
                    </button>
                    <button
                      className="text-button danger"
                      onClick={() => {
                        if (
                          window.confirm(
                            "Diesen gemeinsamen Lauf für alle absagen?",
                          )
                        )
                          action(`/community/${r.id}`, "DELETE");
                      }}
                    >
                      Lauf absagen
                    </button>
                  </>
                )}
              </div>
              <small className="muted">
                Von {r.creator_name} · sichtbar bis{" "}
                {new Date(r.expires_at).toLocaleTimeString("de-CH", {
                  timeZone: "Europe/Zurich",
                  hour: "2-digit",
                  minute: "2-digit",
                })}{" "}
                Uhr
              </small>
            </article>
          ))}
        </div>
      )}
      <p className="muted groups-note">
        Läufe verschwinden automatisch 3 Stunden nach dem Start.
      </p>
      {form && (
        <RunForm
          user={user}
          run={form === "new" ? null : form}
          onClose={closeForm}
          onSaved={() => {
            setForm(null);
            load();
          }}
        />
      )}
      {joining && (
        <Modal title="Ich bin dabei" onClose={closeJoin}>
          <p>
            {joining.distance_km} km · {runDate(joining.starts_at)}
          </p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              action(`/community/${joining.id}/participants`, "POST", { name });
            }}
          >
            <label>
              Dein Name
              <input
                required
                maxLength="60"
                autoComplete="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </label>
            {error && (
              <p className="notice error" role="alert">
                {error}
              </p>
            )}
            <div className="form-actions">
              <button type="button" className="btn" onClick={closeJoin}>
                Abbrechen
              </button>
              <button disabled={busy} className="btn primary">
                {busy ? "Speichern …" : "Teilnehmen"}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </section>
  );
}

import React, { useState } from "react";
import ChallengeProgress, { MiniGrid } from "./ChallengeProgress";

export default function Leaderboard({ people, total }) {
  const [expanded, setExpanded] = useState(null);
  return (
    <section aria-labelledby="ranking-title">
      <div className="total-banner">
        Zusammen haben wir <strong>{total.toLocaleString("de-CH")} km</strong>{" "}
        gesammelt!
      </div>
      <div className="section-heading">
        <h2 id="ranking-title">Rangliste</h2>
        <span className="muted">{people.length} Teilnehmer/innen</span>
      </div>
      <p className="muted">
        Gewertete Kilometer bestimmen den Rang. Eine Person antippen, um alle
        Distanzen zu sehen.
      </p>
      <div className="ranking-guide">
        <span>Teilnehmer/in</span>
        <div className="mini-labels">
          {Array.from({ length: 30 }, (_, i) => (
            <span key={i}>{i + 1}</span>
          ))}
        </div>
        <span>Rang</span>
      </div>
      <div className="ranking-list">
        {people.map((p) => (
          <article
            key={p.id}
            className={`ranking-card${p.completed_count === 30 ? " complete" : ""}`}
          >
            <button
              className="ranking-row"
              aria-expanded={expanded === p.id}
              aria-controls={`runner-${p.id}`}
              onClick={() => setExpanded(expanded === p.id ? null : p.id)}
            >
              <span className="avatar">
                {p.name
                  .split(/\s+/)
                  .slice(0, 2)
                  .map((n) => n[0])
                  .join("")}
              </span>
              <span className="runner-info">
                <strong>{p.name}</strong>
                <span>
                  {p.completed_count}/30 Distanzen · <b>{p.total_score} km</b>
                </span>
              </span>
              <MiniGrid cells={p.cells} />
              <strong className="rank">{p.rank}</strong>
            </button>
            {expanded === p.id && (
              <div id={`runner-${p.id}`} className="runner-detail">
                <p>
                  <strong>{p.name}</strong> · {p.completed_count} Distanzen
                  erledigt
                </p>
                <ChallengeProgress cells={p.cells} compact />
              </div>
            )}
          </article>
        ))}
      </div>
      {!people.length && (
        <div className="empty-state">
          Die Rangliste ist bereit. Mit der ersten Strava-Anmeldung kommt Leben
          in die Challenge.
        </div>
      )}
    </section>
  );
}

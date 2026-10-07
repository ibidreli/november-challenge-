import React, { useState } from "react";
import { challengeDate } from "../time";

export function cellDescription(c) {
  if (c.status === "completed")
    return `${c.km} km: erledigt am ${new Date(c.completed_on + "T12:00:00").toLocaleDateString("de-CH")}`;
  const status = {
    open: "noch offen",
    missed: "Zeitraum abgelaufen",
    scheduled: "kommender Zeitraum",
    upcoming: "noch nicht ausgelost",
  }[c.status];
  return `${c.km} km: ${status}${c.finale ? ` · Abschlusslauf${c.finale_date ? ` am ${challengeDate(c.finale_date)}` : ""}` : c.period ? ` · Woche ${c.period}` : ""}`;
}
export function MiniGrid({ cells }) {
  return (
    <div className="mini-grid" aria-hidden="true">
      {cells.map((c) => (
        <span
          key={c.km}
          className={`mini-cell ${c.status}${c.finale ? " finale" : ""}`}
          title={cellDescription(c)}
        />
      ))}
    </div>
  );
}
export default function ChallengeProgress({ cells, compact = false }) {
  const [selected, setSelected] = useState(null);
  return (
    <div>
      <div
        className={`personal-grid${compact ? " compact" : ""}`}
        aria-label="Distanzen von 1 bis 30 Kilometer"
      >
        {cells.map((c) => (
          <button
            key={c.km}
            className={`distance-cell ${c.status}${c.finale ? " finale" : ""}`}
            title={cellDescription(c)}
            aria-label={cellDescription(c)}
            aria-pressed={selected === c.km}
            onClick={() => setSelected(c.km)}
          >
            <span>{c.km}</span>
            {c.status === "completed" && <small aria-hidden="true">✓</small>}
            {c.finale && c.status !== "completed" && (
              <small aria-hidden="true">★</small>
            )}
          </button>
        ))}
      </div>
      {selected && (
        <p className="cell-detail" aria-live="polite">
          {cellDescription(cells.find((c) => c.km === selected))}
        </p>
      )}
      <div className="legend">
        <span>
          <i className="swatch completed" />
          Erledigt
        </span>
        <span>
          <i className="swatch open" />
          Diese Woche offen
        </span>
        <span>
          <i className="swatch upcoming" />
          Noch nicht ausgelost
        </span>
        {cells.some((c) => c.status === "missed") && (
          <span>
            <i className="swatch missed" />
            Zeitraum abgelaufen
          </span>
        )}
        {cells.some((c) => c.status === "scheduled" && !c.finale) && (
          <span>
            <i className="swatch scheduled" />
            Kommende Woche
          </span>
        )}
        <span>★ Abschlusslauf</span>
      </div>
    </div>
  );
}

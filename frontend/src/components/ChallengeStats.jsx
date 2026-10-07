import React, { useEffect, useRef, useState } from "react";

export default function ChallengeStats({ stats, config }) {
  const [selected, setSelected] = useState(null);
  const [width, setWidth] = useState(770);
  const chart = useRef(null);
  useEffect(() => {
    const observer = new ResizeObserver(([entry]) =>
      setWidth(Math.max(280, Math.round(entry.contentRect.width))),
    );
    observer.observe(chart.current);
    return () => observer.disconnect();
  }, []);
  const points = stats.points.filter((p) => !p.future);
  const shown = points.length
    ? points
    : [{ date: `${config.year}-11-01`, total_km: 0, daily_km: 0 }];
  const maximum = Math.max(...shown.map((p) => p.total_km), 10);
  const position = (p) => [
    48 + ((Number(p.date.slice(-2)) - 1) / 29) * (width - 80),
    200 - (p.total_km / maximum) * 160,
  ];
  const line = shown
    .map((p, i) => `${i ? "L" : "M"}${position(p).join(",")}`)
    .join(" ");
  const active =
    shown.find((p) => p.date === selected) || shown[shown.length - 1];
  return (
    <section className="stats-panel" aria-labelledby="stats-title">
      <div className="section-heading">
        <div>
          <span className="eyebrow">Unsere gemeinsame Challenge</span>
          <h2 id="stats-title">Jeder Lauf bringt uns weiter.</h2>
        </div>
        <div className="stat-total">
          <strong>{stats.total_km.toLocaleString("de-CH")}</strong>
          <span>gewertete km</span>
        </div>
      </div>
      <p className="muted">
        {stats.participants} Teilnehmer/innen · Gezählt werden die abgehakten
        Distanzen. Ein 35-km-Lauf für ein 29-km-Feld trägt 29 km bei.
      </p>
      {!points.length && (
        <p className="notice">
          Am 1. November geht’s los. Hier wächst dann unsere gemeinsame
          Kilometerkurve.
        </p>
      )}
      <svg
        className="km-chart"
        ref={chart}
        viewBox={`0 0 ${width} 245`}
        role="img"
        aria-label={`Gemeinsame gewertete Kilometer im November: ${stats.total_km} Kilometer`}
      >
        <defs>
          <linearGradient id="chart-fill" x1="0" y1="0" x2="0" y2="1">
            <stop stopColor="#14aaa0" stopOpacity=".22" />
            <stop offset="1" stopColor="#14aaa0" stopOpacity=".02" />
          </linearGradient>
        </defs>
        {[0, 0.5, 1].map((t) => (
          <g key={t}>
            <line
              x1="48"
              x2={width - 32}
              y1={200 - t * 160}
              y2={200 - t * 160}
              stroke="#e8eeee"
            />
            <text x="38" y={205 - t * 160} textAnchor="end">
              {Math.round(t * maximum)}
            </text>
          </g>
        ))}
        <path
          d={`${line} L${position(shown[shown.length - 1])[0]},200 L48,200 Z`}
          fill="url(#chart-fill)"
        />
        <path
          d={line}
          fill="none"
          stroke="#07998e"
          strokeWidth="3"
          strokeLinejoin="round"
          strokeLinecap="round"
        />
        {[1, 8, 15, 22, 30].map((day) => (
          <text
            key={day}
            x={48 + ((day - 1) / 29) * (width - 80)}
            y="228"
            textAnchor="middle"
          >
            {day}.11.
          </text>
        ))}
        {points.map((p) => (
          <g key={p.date}>
            <circle
              cx={position(p)[0]}
              cy={position(p)[1]}
              r="4"
              fill="#07998e"
            />
            <circle
              cx={position(p)[0]}
              cy={position(p)[1]}
              r="12"
              fill="transparent"
              role="button"
              tabIndex="0"
              aria-label={`${p.date}: ${p.total_km} km gesamt, ${p.daily_km} km an diesem Tag`}
              onFocus={() => setSelected(p.date)}
              onClick={() => setSelected(p.date)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  setSelected(p.date);
                }
              }}
            />
          </g>
        ))}
      </svg>
      <div className="chart-caption" aria-live="polite">
        {points.length
          ? `${Number(active.date.slice(-2))}. November: ${active.total_km} km gesamt · +${active.daily_km} km an diesem Tag`
          : "Die Kurve zeigt die Summe aller gewerteten Challenge-Kilometer."}
      </div>
    </section>
  );
}

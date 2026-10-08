import React from "react";
import { challengeDate } from "../time";

export default function TestNotice({ config }) {
  if (!config?.test_mode) return null;
  return (
    <div className="notice test-banner" role="note">
      <strong>
        Oktober-Probelauf · {challengeDate(config.starts_on)}–
        {challengeDate(config.finale_date)}
      </strong>
      <span>
        Hier zählen aktuell deine Oktober Läufe.
      </span>
    </div>
  );
}

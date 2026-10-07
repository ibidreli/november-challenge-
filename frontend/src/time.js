const formatter = new Intl.DateTimeFormat("sv-SE", {
  timeZone: "Europe/Zurich",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});
export function localInput(iso) {
  return formatter.format(new Date(iso)).replace(" ", "T");
}
export function zurichToISO(value) {
  const guess = new Date(value + ":00Z");
  if (!Number.isFinite(guess.getTime()))
    throw new Error("Bitte eine gültige Startzeit eingeben.");
  let instant = guess.getTime();
  for (let i = 0; i < 3; i++) {
    const rendered = new Date(localInput(instant) + ":00Z").getTime();
    instant += guess.getTime() - rendered;
  }
  if (localInput(instant) !== value)
    throw new Error(
      "Diese Uhrzeit existiert wegen der Zeitumstellung nicht. Bitte eine andere wählen.",
    );
  return new Date(instant).toISOString();
}
export function runDate(value) {
  return new Date(value).toLocaleString("de-CH", {
    timeZone: "Europe/Zurich",
    weekday: "short",
    day: "numeric",
    month: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
export function pace(value) {
  return `${Math.floor(value / 60)}:${String(value % 60).padStart(2, "0")}`;
}

export function challengeDate(value, long = false) {
  return new Date(value + "T12:00:00Z").toLocaleDateString("de-CH", {
    timeZone: "Europe/Zurich",
    day: "numeric",
    month: long ? "long" : "numeric",
  });
}

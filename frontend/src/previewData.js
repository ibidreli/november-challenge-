// Preview data lives only in the browser. No production API is called in UI mode.
const draw = [5, 6, 9, 14, 19, 24, 27, 29];
const config = {
  year: 2026,
  timezone: "Europe/Zurich",
  finale_km: 15,
  test_mode: false,
  starts_on: "2026-11-01",
  finale_date: "2026-11-30",
  server_date: "2026-11-04",
  periods: [
    [1, 8, 8],
    [9, 15, 7],
    [16, 22, 7],
    [23, 29, 7],
  ].map(([a, b, capacity], i) => ({
    number: i + 1,
    starts_on: `2026-11-${String(a).padStart(2, "0")}`,
    ends_on: `2026-11-${String(b).padStart(2, "0")}`,
    draw_on:
      i === 0 ? "2026-10-31" : `2026-11-${String(a - 1).padStart(2, "0")}`,
    capacity,
    current: i === 0,
    published: i === 0,
    editable: i !== 0,
    distances: i === 0 ? draw : [],
    draft_distances: i === 0 ? draw : [],
  })),
};
let loggedIn = false;
let people = [
  ["Sofia Example", [6, 27, 29]],
  ["Alex Runner", [9, 14, 24]],
  ["Mira Trail", [5, 6, 19]],
  ["Noah Berg", [5, 14]],
].map(([name, done], i) => ({ id: i + 1, name, done }));
let runs = [
  {
    id: "demo",
    creator_name: "Alex Runner",
    distance_km: 9,
    pace_seconds: 360,
    starts_at: new Date(Date.now() + 86400000).toISOString(),
    expires_at: new Date(Date.now() + 97200000).toISOString(),
    latitude: 47.3769,
    longitude: 8.5417,
    meeting_point: "Beim Haupteingang zum Platz",
    participants: ["Alex Runner", "Mira Trail"],
    joined: false,
    can_manage: false,
    can_leave: false,
  },
];
function participant(p, rank) {
  return {
    id: p.id,
    name: p.name,
    rank,
    total_score: p.done.reduce((a, b) => a + b, 0),
    completed_count: p.done.length,
    cells: Array.from({ length: 30 }, (_, i) => ({
      km: i + 1,
      status: p.done.includes(i + 1)
        ? "completed"
        : draw.includes(i + 1)
          ? "open"
          : i === 14
            ? "scheduled"
            : "upcoming",
      period: draw.includes(i + 1) ? 1 : null,
      finale: i === 14,
      finale_date: i === 14 ? config.finale_date : null,
      completed_on: p.done.includes(i + 1) ? "2026-11-03" : null,
    })),
    strava_connected: true,
    last_synced_at: new Date().toISOString(),
  };
}
export function previewLogin(value) {
  loggedIn = value;
}
export async function previewRequest(path, method, body) {
  if (path === "/users/me") {
    if (!loggedIn) throw { response: { status: 401 } };
    return participant(people[0], 1);
  }
  if (path === "/auth/logout") {
    loggedIn = false;
    return {};
  }
  if (path === "/users/") return people.map((p, i) => participant(p, i + 1));
  if (path === "/challenge" || path === "/admin/challenge")
    return structuredClone(config);
  if (path === "/challenge/statistics")
    return {
      total_km: 158,
      participants: people.length,
      points: Array.from({ length: 30 }, (_, i) => ({
        date: `2026-11-${String(i + 1).padStart(2, "0")}`,
        daily_km: [63, 60, 26, 9][i] || 0,
        total_km: [63, 123, 149, 158][Math.min(i, 3)],
        future: i > 3,
      })),
    };
  if (path === "/admin/login") return { token: "preview" };
  if (path === "/admin/users") {
    if (method === "POST") {
      const p = { id: Date.now(), name: body.name, done: [] };
      people.push(p);
      return participant(p, 0);
    }
    return people.map((p, i) => participant(p, i + 1));
  }
  if (path === "/admin/activities") return [];
  if (path === "/admin/community")
    return runs.map((r) => ({ ...r, name: r.creator_name }));
  if (path.startsWith("/admin/challenge/finale")) {
    config.finale_km = body.km;
    return structuredClone(config);
  }
  if (path.startsWith("/admin/challenge/periods/")) {
    const p = config.periods[Number(path.split("/")[4]) - 1];
    p.draft_distances = body.distances;
    p.published = path.endsWith("publish");
    p.distances = p.published ? body.distances : [];
    return structuredClone(config);
  }
  if (path === "/community" && method === "GET")
    return {
      server_now: new Date().toISOString(),
      runs: structuredClone(runs),
    };
  if (path === "/community" && method === "POST") {
    const r = {
      ...body,
      creator_name: body.name,
      id: String(Date.now()),
      expires_at: new Date(
        new Date(body.starts_at).getTime() + 10800000,
      ).toISOString(),
      participants: [body.name],
      joined: true,
      can_manage: true,
      can_leave: false,
    };
    runs.push(r);
    return r;
  }
  if (path.startsWith("/community/")) {
    const id = path.split("/")[2],
      r = runs.find((r) => r.id === id);
    if (method === "DELETE" && path.endsWith("/me")) {
      r.participants.pop();
      r.joined = r.can_leave = false;
    } else if (method === "DELETE") runs = runs.filter((r) => r.id !== id);
    else if (method === "PUT")
      Object.assign(r, body, {
        creator_name: body.name,
        expires_at: new Date(
          new Date(body.starts_at).getTime() + 10800000,
        ).toISOString(),
      });
    else if (!r.joined) {
      r.participants.push(body.name);
      r.joined = r.can_leave = true;
    }
    return r || {};
  }
  return { ok: true };
}

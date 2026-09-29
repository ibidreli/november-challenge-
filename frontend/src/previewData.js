export const previewUser = {
  id: 1,
  name: "Sofia Example",
  total_score: 82,
  slots: [
    5, null, 8, 4, null, 7, null, 10, null, 6,
    null, 3, null, null, 9, null, 5, null, 8, null,
    4, null, null, 6, null, 7, null, null, 5, null,
  ],
};

export const previewLeaderboard = [
  previewUser,
  {
    id: 2,
    name: "Alex Runner",
    total_score: 74,
    slots: [6, null, 5, 8, null, 4, null, 7, null, null, 9, null, 5, null, null, 6, null, 4, null, 8, null, null, 3, null, 7, null, null, 5, null, 4],
  },
  {
    id: 3,
    name: "Mira Trail",
    total_score: 61,
    slots: [null, 4, null, 6, null, 5, null, null, 8, null, 3, null, 5, null, null, 4, null, 7, null, null, 6, null, null, 4, null, null, 5, null, null, null],
  },
];

export const previewAdminUsers = previewLeaderboard.map((user) => ({
  ...user,
  km_total: user.slots.reduce((sum, slot) => sum + (slot || 0), 0),
}));

export const previewActivities = [
  { id: 1, date: "2026-09-04", distance_km: 8.4, effective_km: 8, is_manual: false, status: "claimed" },
  { id: 2, date: "2026-09-08", distance_km: 5.7, effective_km: 5, is_manual: true, status: "claimed" },
  { id: 3, date: "2026-09-15", distance_km: 10.2, effective_km: 10, is_manual: false, status: "claimed" },
];

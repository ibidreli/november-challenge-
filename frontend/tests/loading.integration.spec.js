import { test, expect } from "@playwright/test";

for (const width of [1440, 390]) {
  test(`overview waits for the personal panel before showing ready statistics (${width}px)`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 900 });
    const response = await page.request.get("/users/");
    const person = (await response.json()).find(
      (user) => user.name === "Sofia Integration",
    );
    expect(person).toBeTruthy();
    let releaseAuth;
    const authGate = new Promise((resolve) => {
      releaseAuth = resolve;
    });
    await page.route("**/users/me", async (route) => {
      await authGate;
      await route.fulfill({
        json: {
          ...person,
          strava_connected: true,
          last_synced_at: null,
          sync_error: null,
        },
      });
    });
    const configReady = page.waitForResponse(
      (r) => new URL(r.url()).pathname === "/challenge" && r.ok(),
    );
    const statsReady = page.waitForResponse(
      (r) => new URL(r.url()).pathname === "/challenge/statistics" && r.ok(),
    );
    try {
      await page.goto("/");
      await Promise.all([configReady, statsReady]);
      await expect(
        page.getByRole("status", { name: "Challenge wird geladen" }),
      ).toBeVisible();
      await expect(page.locator(".stats-panel")).toHaveCount(0);
      await expect(page.locator(".personal-panel")).toHaveCount(0);
      releaseAuth();
      await expect(
        page.getByRole("heading", { name: "Hallo Sofia." }),
      ).toBeVisible();
      await expect(page.locator(".stats-panel")).toBeVisible();
      const personal = await page.locator(".personal-panel").boundingBox();
      const stats = await page.locator(".stats-panel").boundingBox();
      expect(personal.y + personal.height).toBeLessThanOrEqual(stats.y);
      await expect(
        page.getByRole("status", { name: "Challenge wird geladen" }),
      ).toHaveCount(0);
    } finally {
      releaseAuth();
    }
  });
}

test("overview renders before statistics, requests ranking only on demand, and reuses tab data", async ({
  page,
}) => {
  const requests = { config: 0, stats: 0, ranking: 0, auth: 0 };
  let releaseStats;
  const statsGate = new Promise((resolve) => {
    releaseStats = resolve;
  });
  await page.route("**/challenge", async (route) => {
    requests.config++;
    await route.continue();
  });
  await page.route("**/users/me", async (route) => {
    requests.auth++;
    await route.continue();
  });
  await page.route("**/users/", async (route) => {
    requests.ranking++;
    await route.continue();
  });
  await page.route("**/challenge/statistics", async (route) => {
    requests.stats++;
    await statsGate;
    await route.continue();
  });
  try {
    await page.goto("/");
    await expect(page.locator(".intro")).toBeVisible();
    await expect(
      page.getByRole("status", { name: "Challenge wird geladen" }),
    ).toBeVisible();
    expect(requests).toEqual({ config: 1, stats: 1, ranking: 0, auth: 1 });
    releaseStats();
    await expect(page.locator(".stats-panel")).toBeVisible();
    await page.getByRole("button", { name: "Rangliste", exact: true }).click();
    await expect(page.locator(".ranking-card").first()).toBeVisible();
    expect(requests.ranking).toBe(1);
    await page.getByRole("button", { name: "Übersicht", exact: true }).click();
    await expect(page.locator(".stats-panel")).toBeVisible();
    await page.getByRole("button", { name: "Rangliste", exact: true }).click();
    await expect(page.locator(".ranking-card").first()).toBeVisible();
    expect(requests).toEqual({ config: 1, stats: 1, ranking: 1, auth: 1 });
  } finally {
    releaseStats();
  }
});

test("statistics failure keeps the overview visible and can be retried", async ({
  page,
}) => {
  let fail = true;
  await page.route("**/challenge/statistics", async (route) => {
    if (fail)
      await route.fulfill({
        status: 503,
        json: { detail: "Statistik vorübergehend nicht verfügbar." },
      });
    else await route.continue();
  });
  await page.goto("/");
  await expect(page.locator(".intro")).toBeVisible();
  await expect(page.getByRole("alert")).toContainText(
    "Statistik vorübergehend",
  );
  fail = false;
  await page.getByRole("button", { name: "Erneut laden", exact: true }).click();
  await expect(page.locator(".stats-panel")).toBeVisible();
  await expect(page.getByRole("alert")).toHaveCount(0);
});

test("loader moves and honours reduced motion while requests are pending", async ({
  page,
}) => {
  let release;
  const gate = new Promise((resolve) => {
    release = resolve;
  });
  await page.route("**/challenge", async (route) => {
    await gate;
    await route.continue();
  });
  try {
    await page.goto("/");
    const loader = page.getByRole("status", { name: "Challenge wird geladen" });
    await expect(loader).toBeVisible();
    const points = await loader.locator("svg").evaluate((svg) => {
      svg.pauseAnimations();
      const leg = svg.querySelector(".runner-front-leg");
      const sample = (time) => {
        svg.setCurrentTime(time);
        const point = leg.getPointAtLength(leg.getTotalLength() - 8);
        return { x: point.x, y: point.y };
      };
      return [sample(0), sample(0.425)];
    });
    expect(Math.abs(points[0].x - points[1].x)).toBeGreaterThan(20);
    await page.emulateMedia({ reducedMotion: "reduce" });
    await expect
      .poll(() =>
        loader
          .locator("svg")
          .evaluate(
            (svg) => svg.animationsPaused() && svg.getCurrentTime() === 0,
          ),
      )
      .toBe(true);
    await page.emulateMedia({ reducedMotion: "no-preference" });
    await expect
      .poll(() =>
        loader.locator("svg").evaluate((svg) => svg.animationsPaused()),
      )
      .toBe(false);
    release();
    await expect(page.locator(".intro")).toBeVisible();
    await expect(loader).toHaveCount(0);
  } finally {
    release();
  }
});

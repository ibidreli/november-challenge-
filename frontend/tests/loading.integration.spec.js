import { test, expect } from "@playwright/test";

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

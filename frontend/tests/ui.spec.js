import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  // Deterministic map tiles; Leaflet itself remains interactive.
  await page.route("https://tile.openstreetmap.org/**", (route) =>
    route.fulfill({
      contentType: "image/svg+xml",
      body: '<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256"><rect width="256" height="256" fill="#e8efeb"/><path d="M0 110 L256 160 M100 0 L150 256" stroke="#fff" stroke-width="12"/></svg>',
    }),
  );
});

test("overview, personal progress, compact ranking and mobile fit", async ({
  page,
}, testInfo) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Jeder Lauf bringt uns weiter." }),
  ).toBeVisible();
  await expect(page.locator(".personal-panel")).toHaveCount(0);
  await page.getByRole("link", { name: /Mit Strava anmelden/ }).click();
  await expect(
    page.getByRole("heading", { name: "Hallo Sofia." }),
  ).toBeVisible();
  await expect(page.getByText("Noch offen:")).toContainText("5 km");
  await expect(
    page.locator(".personal-panel .distance-cell.completed"),
  ).toHaveCount(3);
  await page.getByRole("button", { name: /^29 km: erledigt/ }).click();
  await expect(page.locator(".cell-detail")).toContainText("erledigt am");
  await page.screenshot({
    path: `../output/verification/overview-${testInfo.project.name}.png`,
    fullPage: true,
  });
  await page.getByRole("button", { name: "Rangliste", exact: true }).click();
  await expect(page.locator(".ranking-card")).toHaveCount(4);
  await page.getByRole("button", { name: /Sofia Example.*3\/30/ }).click();
  await expect(page.locator(".runner-detail .distance-cell")).toHaveCount(30);
  await page.getByRole("button", { name: /Alex Runner.*3\/30/ }).click();
  await expect(page.locator(".runner-detail")).toHaveCount(1);
  await page.screenshot({
    path: `../output/verification/ranking-${testInfo.project.name}.png`,
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  expect(errors).toEqual([]);
});

test("guest creates a mapped run, joins another and can leave", async ({
  page,
}, testInfo) => {
  await page.goto("/?tab=groups");
  await expect(page.locator(".leaflet-container")).toBeVisible();
  await page
    .getByRole("button", { name: /Lauf erstellen/ })
    .first()
    .click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Dein Name").fill("Elias Gast");
  await dialog.getByLabel("Distanz in km").fill("12");
  await dialog.getByLabel(/Voraussichtliche Pace/).fill("5:45");
  await dialog.getByLabel(/Tag und Startzeit/).fill("2026-11-10T18:30");
  await dialog
    .getByRole("button", { name: "Kartenmitte als Startpunkt" })
    .click();
  await dialog.getByLabel("Treffpunkt kurz beschreiben").fill("Beim Brunnen");
  await page.screenshot({
    path: `../output/verification/group-form-${testInfo.project.name}.png`,
    fullPage: true,
  });
  await dialog.getByRole("button", { name: "Lauf speichern" }).click();
  await expect(
    page.getByRole("heading", { name: "12 km gemeinsam laufen" }),
  ).toBeVisible();
  await expect(
    page.locator(".group-card").filter({ hasText: "Beim Brunnen" }),
  ).toContainText("Elias Gast");
  await page
    .getByRole("button", { name: "Teilnehmen", exact: true })
    .first()
    .click();
  await page.getByRole("dialog").getByLabel("Dein Name").fill("Elias Gast");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Teilnehmen", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Nicht mehr teilnehmen" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Nicht mehr teilnehmen" }).click();
  await expect(
    page.getByRole("button", { name: "Nicht mehr teilnehmen" }),
  ).toHaveCount(0);
  await page.screenshot({
    path: `../output/verification/groups-${testInfo.project.name}.png`,
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
});

test("Swiss start times are independent of browser timezone", async ({
  page,
}) => {
  await page.goto("/");
  const values = await page.evaluate(async () => {
    const { zurichToISO, localInput } = await import("/src/time.js");
    return [
      zurichToISO("2026-11-10T18:30"),
      zurichToISO("2026-10-10T18:30"),
      localInput("2026-11-10T17:30:00Z"),
    ];
  });
  expect(values).toEqual([
    "2026-11-10T17:30:00.000Z",
    "2026-10-10T16:30:00.000Z",
    "2026-11-10T18:30",
  ]);
});

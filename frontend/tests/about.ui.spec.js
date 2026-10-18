import { test, expect } from "@playwright/test";

test("info link opens the team and past editions with a clear return to the challenge", async ({
  page,
}) => {
  await page.goto("/");
  const info = page.getByRole("link", { name: "Über uns", exact: true });
  await expect(info).toBeVisible();
  const icon = await info.boundingBox();
  const login = await page
    .getByRole("link", { name: "Mit Strava anmelden" })
    .boundingBox();
  expect(icon.x + icon.width).toBeLessThan(login.x);
  await info.click();
  await expect(page).toHaveURL(/\/about$/);
  await expect(
    page.getByRole("heading", { level: 1, name: "Über uns" }),
  ).toBeVisible();
  await expect(page).toHaveTitle("Über uns · November Challenge");
  for (const name of ["Yänu", "Oli", "Eli"]) {
    await expect(
      page.getByRole("heading", { name, exact: true }),
    ).toBeVisible();
  }
  const year2025 = page
    .locator(".about-edition")
    .filter({ has: page.getByRole("heading", { name: "2025", exact: true }) });
  const year2024 = page
    .locator(".about-edition")
    .filter({ has: page.getByRole("heading", { name: "2024", exact: true }) });
  await expect(year2025.locator(".about-finishers li")).toHaveCount(8);
  await expect(year2025).toContainText("Lukas Hohwald");
  await expect(year2025).toContainText("Samuel Skott");
  await expect(year2025.getByRole("row")).toHaveCount(4);
  await expect(year2024.locator(".about-finishers li")).toHaveCount(2);
  await expect(year2024).toContainText("Franziskus Heinzmann");
  await expect(year2024).toContainText("Thierry Kneissler");
  await expect(year2024).toContainText("465 Kilometer");
  await page
    .getByRole("link", { name: "Zurück zur Challenge", exact: true })
    .last()
    .click();
  await expect(page).toHaveURL(/\/$/);
  await expect(
    page.getByRole("heading", { name: "Jeder Lauf bringt uns weiter." }),
  ).toBeVisible();
  await expect(page).toHaveTitle("November Challenge");
});

test("authenticated navigation preserves login, the previous tab, and browser history", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Mit Strava anmelden" }).click();
  await expect(
    page.getByRole("heading", { name: "Hallo Sofia." }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Rangliste", exact: true }).click();
  await expect(page.locator(".ranking-card")).toHaveCount(4);
  await page.getByRole("link", { name: "Über uns", exact: true }).click();
  await expect(page).toHaveURL(/\/about\?from=ranking$/);
  await expect(
    page.getByRole("button", { name: "Abmelden", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("link", { name: "Zurück zur Challenge", exact: true })
    .first()
    .click();
  await expect(page).toHaveURL(/\/\?tab=ranking$/);
  await expect(page.locator(".ranking-card")).toHaveCount(4);
  await page.goBack();
  await expect(
    page.getByRole("heading", { name: "Über uns", exact: true }),
  ).toBeVisible();
  await page.goBack();
  await expect(page.locator(".ranking-card")).toHaveCount(4);
  await page.getByRole("button", { name: "Übersicht", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Hallo Sofia." }),
  ).toBeVisible();
});

test("direct about links reload correctly and fit mobile and tablet widths", async ({
  page,
}, testInfo) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/about");
  await expect(
    page.getByRole("heading", { name: "Über uns", exact: true }),
  ).toBeVisible();
  await page.reload();
  await expect(page.locator(".about-member")).toHaveCount(3);
  const widths =
    testInfo.project.name === "mobile" ? [320, 390] : [768, 1024, 1440];
  for (const width of widths) {
    await page.setViewportSize({ width, height: 900 });
    await expect(
      page.getByRole("link", { name: "Über uns", exact: true }),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBeTruthy();
  }
  await page.screenshot({
    path: `../output/verification/about-${testInfo.project.name}.png`,
    fullPage: true,
  });
  await page
    .getByRole("link", { name: "Zurück zur Challenge", exact: true })
    .first()
    .click();
  await expect(
    page.getByRole("heading", { name: "Jeder Lauf bringt uns weiter." }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});

import { test, expect } from "@playwright/test";

test("October calendar: real API, admin setup, scoring and responsive chart", async ({
  page,
  context,
}) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.clock.install({ time: new Date("2026-10-07T12:00:00Z") });
  await context.addCookies([
    {
      name: "nc_session",
      value: "e2e-user-session",
      domain: "localhost",
      path: "/",
    },
  ]);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.getByRole("note")).toContainText("Testumgebung");
  await expect(page.getByRole("note")).toContainText("1.10.");
  await expect(page.locator(".personal-panel")).toContainText("0 km");
  await page.goto("/admin");
  await page.getByLabel("Admin-Passwort").fill("e2e-only-password");
  await page.getByRole("button", { name: "Anmelden", exact: true }).click();
  await page.getByLabel("Beginn des Tests").fill("2026-10-01");
  for (let i = 1; i <= 4; i++)
    await expect(page.getByLabel(`Tage im Zeitraum ${i}`)).toHaveValue(
      i === 1 ? "8" : "7",
    );
  await page.getByRole("button", { name: "Testkalender speichern" }).click();
  await expect(page.getByRole("status")).toContainText(
    "Testkalender gespeichert",
  );
  await expect(page.getByLabel(/Abschlusslauf am 30.10./)).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: "../output/verification/october-admin-mobile.png",
    fullPage: true,
  });
  const first = page
    .locator(".draw-card")
    .filter({
      has: page.getByRole("heading", { name: "Woche 1", exact: true }),
    });
  await first
    .getByLabel("Ausgeloste Distanzen in km")
    .fill("5,6,9,14,19,24,27,29");
  await first.getByRole("button", { name: "Veröffentlichen" }).click();
  await expect(page.getByRole("status")).toContainText("veröffentlicht");
  await expect(page.getByLabel("Beginn des Tests")).toBeDisabled();
  await page.goto("/");
  await expect(page.locator(".personal-panel")).toContainText("62 km");
  await expect(
    page.locator(".personal-panel .distance-cell.completed"),
  ).toHaveCount(3);
  await page.getByRole("button", { name: /^15 km:/ }).click();
  await expect(page.locator(".cell-detail")).toContainText("30.10.");
  await expect(page.locator(".km-chart")).toContainText("30.10.");
  await expect(page.locator(".km-chart")).not.toContainText(".11.");
  for (const [name, width, height] of [
    ["mobile", 390, 844],
    ["desktop", 1440, 1000],
  ]) {
    await page.setViewportSize({ width, height });
    await page.screenshot({
      path: `../output/verification/october-overview-${name}.png`,
      fullPage: true,
    });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBeTruthy();
  }
  await page.getByRole("button", { name: "Rangliste", exact: true }).click();
  await expect(page.locator(".ranking-card")).toContainText("62 km");
  await page.reload();
  await expect(page.getByRole("note")).toContainText("Testumgebung");
  await expect(
    page.getByRole("button", { name: "Abmelden", exact: true }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});

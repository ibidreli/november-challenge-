import { test, expect } from "@playwright/test";

test("real API: cookie login, manual correction, draw publication and guest persistence", async ({
  page,
  context,
}) => {
  await page.clock.install({ time: new Date("2026-11-04T12:00:00Z") });
  await context.addCookies([
    {
      name: "nc_session",
      value: "e2e-user-session",
      domain: "localhost",
      path: "/",
    },
  ]);
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Hallo Sofia." }),
  ).toBeVisible();
  await expect(page.locator(".personal-panel")).toContainText("62 km");
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Abmelden", exact: true }),
  ).toBeVisible();
  await page.goto("/admin");
  await page.getByLabel("Admin-Passwort").fill("e2e-only-password");
  await page.getByRole("button", { name: "Anmelden", exact: true }).click();
  const week2 = page
    .locator(".draw-card")
    .filter({ has: page.getByRole("heading", { name: "Woche 2" }) });
  await week2.getByLabel("Ausgeloste Distanzen in km").fill("1,2,3,4,7,8,10");
  await week2.getByRole("button", { name: "Entwurf speichern" }).click();
  await expect(page.getByRole("status")).toContainText("Entwurf gespeichert");
  const draft = await page.request.get("/challenge");
  expect((await draft.json()).periods[1].distances).toEqual([]);
  await week2.getByRole("button", { name: "Veröffentlichen" }).click();
  await expect(page.getByRole("status")).toContainText("veröffentlicht");
  await page.getByRole("button", { name: "Aktivitäten", exact: true }).click();
  await page
    .getByRole("combobox", { name: "Teilnehmer", exact: true })
    .selectOption({ label: "Sofia Integration" });
  await page.getByLabel("Laufdatum").fill("2026-11-01");
  await page.getByLabel("Tatsächlich gelaufene km").fill("7");
  await page.getByRole("button", { name: "Korrektur speichern" }).click();
  await expect(page.getByRole("status")).toContainText("Wertung aktualisiert");
  await page.getByRole("button", { name: "Challenge", exact: true }).click();
  const week1 = page
    .locator(".draw-card")
    .filter({ has: page.getByRole("heading", { name: "Woche 1" }) });
  const distances = week1.getByLabel("Ausgeloste Distanzen in km");
  await expect(distances).toBeDisabled();
  page.once("dialog", (dialog) => dialog.dismiss());
  await week1.getByRole("button", { name: "Auslosung zurücksetzen" }).click();
  await expect(distances).toBeDisabled();
  page.once("dialog", (dialog) => dialog.accept());
  await week1.getByRole("button", { name: "Auslosung zurücksetzen" }).click();
  await expect(page.getByRole("status")).toContainText(
    "Auslosung zurückgesetzt",
  );
  await expect(distances).toBeEnabled();
  await expect(distances).toHaveValue("");
  const cleared = await page.request.get("/users/");
  expect(
    (await cleared.json()).find((user) => user.name === "Sofia Integration")
      .total_score,
  ).toBe(0);
  await distances.fill("5,6,9,14,19,24,27,28");
  await week1
    .getByRole("button", { name: "Veröffentlichen", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText(
    "Auslosung veröffentlicht",
  );
  await expect(distances).toBeDisabled();
  await page.goto("/");
  await expect(page.locator(".personal-panel")).toContainText("39 km"); // existing runs re-score: manual 7->6, day2 30->28, day3 7->5
  await page.getByRole("button", { name: "Abmelden", exact: true }).click();
  await expect(
    page.getByRole("link", { name: /Mit Strava anmelden/ }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Laufgruppen", exact: true })
    .click();
  await page
    .getByRole("button", { name: /Lauf erstellen/ })
    .first()
    .click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Dein Name").fill("Gast mit Cookie");
  await dialog.getByLabel("Distanz in km").fill("9");
  // Use a future date in Swiss local time.
  const future = await page.evaluate(async () =>
    (await import("/src/time.js")).localInput(Date.now() + 86400000),
  );
  await dialog.getByLabel(/Tag und Startzeit/).fill(future);
  await dialog
    .getByRole("button", { name: "Kartenmitte als Startpunkt" })
    .click();
  await dialog
    .getByLabel("Treffpunkt kurz beschreiben")
    .fill("Beim Testbahnhof");
  await dialog.getByRole("button", { name: "Lauf speichern" }).click();
  await expect(
    page.getByRole("heading", { name: "9 km gemeinsam laufen" }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Lauf absagen" }),
  ).toBeVisible();
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "Lauf absagen" }).click();
  await expect(
    page.getByText("Noch kein gemeinsamer Lauf geplant."),
  ).toBeVisible();
});

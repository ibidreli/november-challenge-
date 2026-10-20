import { test, expect } from "@playwright/test";

test("footer opens the legal page and returns to the previous challenge tab", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Rangliste", exact: true }).click();
  await expect(page.locator(".ranking-card")).toHaveCount(4);
  const footer = page.getByRole("navigation", {
    name: "Rechtliches und Verwaltung",
  });
  await expect(
    footer.getByRole("link", { name: "Admin", exact: true }),
  ).toHaveAttribute("href", "/admin");
  await footer
    .getByRole("link", { name: "AGB & Datenschutz", exact: true })
    .click();
  await expect(page).toHaveURL(/\/agb\?from=ranking$/);
  await expect(
    page.getByRole("heading", { level: 1, name: "AGB & Datenschutz" }),
  ).toBeFocused();
  await expect(page).toHaveTitle("AGB & Datenschutz · November Challenge");
  await expect(
    footer.getByRole("link", { name: "AGB & Datenschutz", exact: true }),
  ).toHaveAttribute("aria-current", "page");
  await page.getByRole("link", { name: "Kontakt", exact: true }).click();
  await expect(page).toHaveURL(/#kontakt$/);
  const contact = page.locator(".legal-contact");
  await expect(contact).toContainText("Elias Pulver");
  await expect(contact).toContainText("Mülchistrasse 4");
  await expect(contact).toContainText("3317 Limpach");
  await expect(
    contact.getByRole("link", { name: "eliaspulver@gmail.com" }),
  ).toHaveAttribute("href", "mailto:eliaspulver@gmail.com");
  await page
    .getByRole("link", { name: "Zurück zur Challenge", exact: true })
    .last()
    .click();
  await expect(page).toHaveURL(/\/\?tab=ranking$/);
  await expect(page.locator(".ranking-card")).toHaveCount(4);
  await expect(page).toHaveTitle("November Challenge");
});

test("legal navigation preserves the logged-in account and browser history", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Mit Strava anmelden" }).click();
  await expect(
    page.getByRole("heading", { name: "Hallo Sofia." }),
  ).toBeVisible();
  await page
    .locator("footer")
    .getByRole("link", { name: "AGB & Datenschutz" })
    .click();
  await expect(
    page.getByRole("button", { name: "Abmelden", exact: true }),
  ).toBeVisible();
  await page.goBack();
  await expect(
    page.getByRole("heading", { name: "Hallo Sofia." }),
  ).toBeVisible();
  await page.goForward();
  await expect(
    page.getByRole("heading", { level: 1, name: "AGB & Datenschutz" }),
  ).toBeVisible();
  await page
    .getByRole("link", { name: "Zurück zur Challenge", exact: true })
    .last()
    .click();
  await expect(
    page.getByRole("heading", { name: "Hallo Sofia." }),
  ).toBeVisible();
});

test("direct legal links reload, section anchors work and the page fits small screens", async ({
  page,
}, testInfo) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/agb");
  await page.reload();
  await expect(
    page.getByRole("heading", { level: 1, name: "AGB & Datenschutz" }),
  ).toBeVisible();
  await page
    .getByRole("navigation", { name: "Inhalt der Rechtstexte" })
    .getByRole("link", { name: "Datenschutz", exact: true })
    .click();
  await expect(page).toHaveURL(/\/agb#datenschutz$/);
  await expect(
    page.getByRole("heading", { name: "Datenschutzerklärung", exact: true }),
  ).toBeInViewport();
  await page.goto("/agb");
  const widths =
    testInfo.project.name === "mobile" ? [320, 390] : [768, 1024, 1440];
  for (const width of widths) {
    await page.setViewportSize({ width, height: 900 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBeTruthy();
  }
  await page.screenshot({
    path: `../output/verification/legal-${testInfo.project.name}.png`,
  });
  await page.locator(".legal-contact").screenshot({
    path: `../output/verification/legal-contact-${testInfo.project.name}.png`,
  });
  expect(errors).toEqual([]);
});

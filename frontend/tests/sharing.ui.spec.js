import { test, expect } from "@playwright/test";
import { readFile } from "node:fs/promises";

test.beforeEach(async ({ page }) => {
  await page.route("https://tile.openstreetmap.org/**", (route) =>
    route.fulfill({
      contentType: "image/svg+xml",
      headers: { "Access-Control-Allow-Origin": "*" },
      body: '<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256"><rect width="256" height="256" fill="#e8efeb"/><path d="M0 110 L256 160 M100 0 L150 256" stroke="#fff" stroke-width="12"/></svg>',
    }),
  );
});

test("one image action downloads the PNG when native sharing is unavailable", async ({
  page,
}, testInfo) => {
  await page.addInitScript(() =>
    Object.defineProperty(navigator, "share", {
      configurable: true,
      value: undefined,
    }),
  );
  await page.goto("/?tab=groups");
  await page.getByRole("button", { name: /^Lauf teilen:/ }).click();
  const dialog = page.getByRole("dialog", { name: "Bild teilen" });
  const image = dialog.getByRole("img");
  await expect(image).toBeVisible();
  await expect.poll(() => image.evaluate((img) => img.naturalWidth)).toBe(1080);
  expect(await image.evaluate((img) => img.naturalHeight)).toBeLessThan(1400);
  await expect(dialog.locator(".share-action")).toHaveCount(1);
  await expect(dialog.getByRole("link")).toHaveCount(0);
  await expect(dialog.getByRole("textbox")).toHaveCount(0);
  const downloading = page.waitForEvent("download");
  await dialog
    .getByRole("button", { name: "Bild teilen", exact: true })
    .click();
  const download = await downloading;
  expect(download.suggestedFilename()).toBe("laufgruppe-demo.png");
  const path = `../output/verification/run-share-${testInfo.project.name}.png`;
  await download.saveAs(path);
  const png = await readFile(path);
  expect([...png.subarray(0, 8)]).toEqual([137, 80, 78, 71, 13, 10, 26, 10]);
  expect(png.length).toBeGreaterThan(5000);
  await page.screenshot({
    path: `../output/verification/share-dialog-${testInfo.project.name}.png`,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
});

test("native image share uses only the groups tab link and handles cancellation", async ({
  page,
}) => {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, "canShare", {
      configurable: true,
      value: (data) => data.files?.[0] instanceof File,
    });
    Object.defineProperty(navigator, "share", {
      configurable: true,
      value: async (data) => {
        window.sharedRun = {
          url: data.url,
          text: data.text,
          type: data.files[0].type,
          size: data.files[0].size,
          active: navigator.userActivation.isActive,
        };
        if (window.shareFailure)
          throw new DOMException("Test", window.shareFailure);
      },
    });
  });
  await page.goto("/?tab=groups&run=ignored&auth_error=old");
  await page.getByRole("button", { name: /^Lauf teilen:/ }).click();
  const dialog = page.getByRole("dialog", { name: "Bild teilen" });
  const share = dialog.getByRole("button", {
    name: "Bild teilen",
    exact: true,
  });
  await share.click();
  const received = await page.evaluate(() => window.sharedRun);
  expect(received).toMatchObject({ type: "image/png", active: true });
  expect(received.text).toBeUndefined();
  expect(new URL(received.url).search).toBe("?tab=groups");
  await page.evaluate(() => {
    window.shareFailure = "AbortError";
  });
  await share.click();
  await expect(dialog.getByRole("status")).toHaveCount(0);
  await page.evaluate(() => {
    window.shareFailure = "NotAllowedError";
  });
  const downloading = page.waitForEvent("download");
  await share.click();
  expect((await downloading).suggestedFilename()).toBe("laufgruppe-demo.png");
});

test("a missing map still allows image export through the same action", async ({
  page,
}) => {
  await page.addInitScript(() =>
    Object.defineProperty(navigator, "share", {
      configurable: true,
      value: undefined,
    }),
  );
  await page.route("https://tile.openstreetmap.org/**", (route) =>
    route.abort(),
  );
  await page.goto("/?tab=groups");
  await page.getByRole("button", { name: /^Lauf teilen:/ }).click();
  const dialog = page.getByRole("dialog", { name: "Bild teilen" });
  await expect(dialog.getByRole("img")).toBeVisible();
  const downloading = page.waitForEvent("download");
  await dialog
    .getByRole("button", { name: "Bild teilen", exact: true })
    .click();
  expect((await downloading).suggestedFilename()).toBe("laufgruppe-demo.png");
});

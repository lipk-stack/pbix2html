import { mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { expect, test } from "@playwright/test";
import type { DashboardIR } from "@pbix2html/dir-schema";
import { exportSingleFileHtml } from "@pbix2html/html-exporter";

let filePath: string;

test.beforeAll(async () => {
  const fixturePath = new URL("../../fixtures/sales-report/report.json", import.meta.url);
  const ir = JSON.parse(await readFile(fixturePath, "utf-8")) as DashboardIR;
  const { html } = await exportSingleFileHtml(ir);
  const dir = await mkdtemp(join(tmpdir(), "pbix2html-e2e-"));
  filePath = join(dir, "dashboard.html");
  await writeFile(filePath, html, "utf-8");
});

test.describe("Sales Executive Summary — offline acceptance", () => {
  test("loads offline and slicer + cross-filter interactions update only the wired visuals", async ({
    page,
    context,
  }) => {
    const requests: string[] = [];
    page.on("request", (req) => requests.push(req.url()));
    await context.setOffline(true);

    await page.goto(`file://${filePath}`);

    const totalRevenue = page.locator('[data-visual-id="card-total-revenue"] .pbix-card-value');
    const avgPrice = page.locator('[data-visual-id="card-avg-selling-price"] .pbix-card-value');

    await expect(totalRevenue).toHaveText("$746,000");
    await expect(avgPrice).toHaveText("$238.72");

    await page.locator('[data-visual-id="slicer-year"] button', { hasText: "2023" }).click();
    await expect(totalRevenue).toHaveText("$249,000");
    await expect(avgPrice).toHaveText("$240.58");

    await page.locator('[data-visual-id="bar-revenue-by-category"] rect[data-category="Bikes"]').click();
    await expect(totalRevenue).toHaveText("$150,000");
    await expect(avgPrice).toHaveText("$1,578.95");

    // Clicking the same bar again toggles the cross-filter off.
    await page.locator('[data-visual-id="bar-revenue-by-category"] rect[data-category="Bikes"]').click();
    await expect(totalRevenue).toHaveText("$249,000");

    // Clearing the slicer returns to the fully unfiltered baseline.
    await page.locator('[data-visual-id="slicer-year"] button', { hasText: "2023" }).click();
    await expect(totalRevenue).toHaveText("$746,000");

    const networkRequests = requests.filter((url) => url.startsWith("http://") || url.startsWith("https://"));
    expect(networkRequests).toEqual([]);
  });

  test("cross-filtering a category does not affect the bar chart's own category list", async ({ page }) => {
    await page.goto(`file://${filePath}`);
    const bars = page.locator('[data-visual-id="bar-revenue-by-category"] rect.pbix-bar');
    await expect(bars).toHaveCount(4);

    await bars.nth(1).click();
    // The bar chart is not wired as its own interaction target, so it must still show all 4 categories.
    await expect(bars).toHaveCount(4);
    await expect(page.locator('[data-visual-id="bar-revenue-by-category"] rect.pbix-bar-selected')).toHaveCount(1);
  });

  test("bars are keyboard-operable", async ({ page }) => {
    await page.goto(`file://${filePath}`);
    const firstBar = page.locator('[data-visual-id="bar-revenue-by-category"] rect.pbix-bar').first();
    await firstBar.focus();
    await page.keyboard.press("Enter");
    await expect(page.locator('[data-visual-id="bar-revenue-by-category"] rect.pbix-bar-selected')).toHaveCount(1);
  });
});

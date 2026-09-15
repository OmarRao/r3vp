/*
 * Copyright (c) 2026 Omar Rao
 * SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
 * This file is available under the GNU Affero General Public License v3.0
 * or under a separate commercial license.
 */
import { expect, test } from "@playwright/test";

test.describe("portal smoke", () => {
  test("demo login page renders", async ({ page }) => {
    await page.goto("/demo/login");
    await expect(page.getByText("Sign in to demo")).toBeVisible();
  });

  test("dashboard renders via dev preview", async ({ page }) => {
    await page.goto("/dashboard");
    // Sidebar navigation is present regardless of backend data.
    await expect(page.getByRole("link", { name: "Workloads" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Threat Scanner" })).toBeVisible();
  });

  test("workloads page renders its heading", async ({ page }) => {
    await page.goto("/dashboard/workloads");
    await expect(page.getByRole("heading", { name: "Workloads" })).toBeVisible();
  });

  test("theme toggle switches the theme", async ({ page }) => {
    await page.goto("/dashboard");
    const html = page.locator("html");
    const wasDark = await html.evaluate((el) => el.classList.contains("dark"));
    await page.getByRole("button", { name: /switch to (dark|light) mode/i }).first().click();
    const nowDark = await html.evaluate((el) => el.classList.contains("dark"));
    expect(nowDark).toBe(!wasDark);
  });
});

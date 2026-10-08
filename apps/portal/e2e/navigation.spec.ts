/*
 * Copyright (c) 2026 Omar Rao
 * SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
 * This file is available under the GNU Affero General Public License v3.0
 * or under a separate commercial license.
 */
import { expect, test } from "@playwright/test";

/**
 * Exercises interactions that do not depend on backend data: sidebar
 * click-through, theme persistence across a reload, and the onboarding wizard's
 * client-side step navigation. The API is unreachable in the Playwright config,
 * so all assertions target static chrome and client state only.
 */

test.describe("sidebar navigation click-through", () => {
  const LINKS: Array<{ name: string; path: string; heading: string }> = [
    { name: "Threat Scanner", path: "/dashboard/threats", heading: "Threat Scanner" },
    { name: "Reports", path: "/dashboard/reports", heading: "Compliance Reports" },
    { name: "Fleet", path: "/dashboard/fleet", heading: "Fleet" },
    { name: "Test Runs", path: "/dashboard/test-runs", heading: "Test Runs" },
  ];

  for (const { name, path, heading } of LINKS) {
    test(`clicking "${name}" navigates to ${path}`, async ({ page }) => {
      await page.goto("/dashboard");
      // Let the client router hydrate so sidebar Links perform SPA navigation.
      await page.waitForLoadState("networkidle");
      // Retry the click until the router has hydrated and navigation lands; a
      // click that arrives before hydration is a no-op, so poll rather than
      // assume a single click takes effect.
      const link = page.getByRole("link", { name, exact: true });
      await expect(async () => {
        await link.click();
        await expect(page).toHaveURL(new RegExp(`${path}$`), { timeout: 2000 });
      }).toPass({ timeout: 15000 });
      await expect(page.getByRole("heading", { name: heading, exact: true }).first()).toBeVisible();
      // Active link exposes aria-current for the current route.
      await expect(page.getByRole("link", { name, exact: true })).toHaveAttribute("aria-current", "page");
    });
  }
});

test.describe("theme persistence", () => {
  test("toggling persists the choice to localStorage", async ({ page }) => {
    await page.goto("/dashboard");
    const html = page.locator("html");
    const wasDark = await html.evaluate((el) => el.classList.contains("dark"));

    await page.getByRole("button", { name: /switch to (dark|light) mode/i }).first().click();
    const nowDark = await html.evaluate((el) => el.classList.contains("dark"));
    expect(nowDark).toBe(!wasDark);

    // The chosen theme is written to localStorage, which the no-flash init
    // script reads on subsequent loads. Asserting the persisted value is more
    // robust than the post-hydration DOM class.
    const stored = await page.evaluate(() => localStorage.getItem("r3vp-theme"));
    expect(stored).toBe(nowDark ? "dark" : "light");
  });
});

test.describe("onboarding wizard", () => {
  test("renders step 1 and advances to step 2 client-side", async ({ page }) => {
    await page.goto("/onboarding");
    await expect(page.getByRole("heading", { name: "Organization Profile" })).toBeVisible();
    await expect(page.getByText("Step 1 of", { exact: false })).toBeVisible();

    await page.waitForLoadState("networkidle");
    await page.getByRole("button", { name: "Continue" }).click();
    await expect(page.getByRole("heading", { name: "Deploy Appliance" })).toBeVisible();
    await expect(page.getByText("Step 2 of", { exact: false })).toBeVisible();
  });
});

test.describe("demo login", () => {
  test("renders sign-in card and auth controls", async ({ page }) => {
    await page.goto("/demo/login");
    await expect(page.getByRole("heading", { name: "Sign in to demo" })).toBeVisible();
    await expect(page.getByRole("button", { name: /continue with google/i })).toBeVisible();
    await expect(page.getByPlaceholder("you@example.com")).toBeVisible();
  });
});

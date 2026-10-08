/*
 * Copyright (c) 2026 Omar Rao
 * SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
 * This file is available under the GNU Affero General Public License v3.0
 * or under a separate commercial license.
 */
import { expect, test } from "@playwright/test";

/**
 * Every dashboard route must render its primary heading (an <h1>) via the
 * dev-preview auth bypass, independent of backend data. The API is pointed at a
 * dead port in the Playwright config, so each page is expected to render its
 * chrome and heading while data falls into loading/empty states. Assertions
 * therefore target the static heading text only.
 */
const DASHBOARD_ROUTES: Array<{ path: string; heading: string }> = [
  { path: "/dashboard", heading: "Recovery Readiness Dashboard" },
  { path: "/dashboard/workloads", heading: "Workloads" },
  { path: "/dashboard/test-runs", heading: "Test Runs" },
  { path: "/dashboard/appliances", heading: "Appliances" },
  { path: "/dashboard/threats", heading: "Threat Scanner" },
  { path: "/dashboard/incidents", heading: "Incidents" },
  { path: "/dashboard/continuous-validation", heading: "Continuous Validation" },
  { path: "/dashboard/reports", heading: "Compliance Reports" },
  { path: "/dashboard/runbooks", heading: "DR Runbooks" },
  { path: "/dashboard/fleet", heading: "Fleet" },
  { path: "/dashboard/mssp", heading: "MSSP Console" },
  { path: "/dashboard/providers", heading: "Multi-Cloud Providers" },
  { path: "/dashboard/insights", heading: "AI Insights" },
  { path: "/dashboard/integrations", heading: "Integrations" },
  { path: "/dashboard/settings", heading: "Settings" },
  { path: "/dashboard/settings/team", heading: "Team Management" },
];

test.describe("dashboard pages render their headings", () => {
  for (const { path, heading } of DASHBOARD_ROUTES) {
    test(`${path} renders "${heading}"`, async ({ page }) => {
      await page.goto(path);
      await expect(page.getByRole("heading", { name: heading, exact: true }).first()).toBeVisible();
      // The dark-navy sidebar chrome renders on every dashboard page.
      await expect(page.getByRole("link", { name: "Workloads" })).toBeVisible();
    });
  }
});

"use client";
/*
 * Copyright (c) 2026 Omar Rao
 * SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
 * This file is available under the GNU Affero General Public License v3.0
 * or under a separate commercial license.
 */


import type { Route } from "next";
import Link from "next/link";
import { usePathname } from "next/navigation";

const ROUTE_LABELS: Record<string, string> = {
  dashboard: "Dashboard",
  workloads: "Workloads",
  "test-runs": "Test Runs",
  appliances: "Appliances",
  providers: "Providers",
  reports: "Reports",
  schedule: "Scheduled Delivery",
  runbooks: "DR Runbooks",
  threats: "Threat Scanner",
  incidents: "Incidents",
  integrations: "Integrations",
  insights: "AI Insights",
  mssp: "MSSP Console",
  "continuous-validation": "Continuous Validation",
  fleet: "Fleet",
  settings: "Settings",
  team: "Team",
  sso: "Single Sign-On",
};

export function Breadcrumb() {
  const pathname = usePathname();
  const segments = pathname.split("/").filter(Boolean);

  // Build cumulative paths
  const crumbs = segments.map((seg, i) => ({
    label: ROUTE_LABELS[seg] ?? seg,
    href: "/" + segments.slice(0, i + 1).join("/"),
    isLast: i === segments.length - 1,
  }));

  if (crumbs.length <= 1) return null;

  // Theme-aware colors read the CSS variables defined in globals.css.
  const c = {
    surface2: "rgb(var(--color-surface-2))",
    content: "rgb(var(--color-content))",
    muted: "rgb(var(--color-content-muted))",
    border: "rgb(var(--color-border))",
  };

  return (
    <nav
      aria-label="Breadcrumb"
      style={{
        flexShrink: 0, background: c.surface2, borderBottom: `1px solid ${c.border}`,
        padding: "0 28px", height: 32, display: "flex", alignItems: "center",
        gap: 6, fontSize: 11,
      }}
    >
      <Link href="/dashboard" style={{ color: c.muted, fontWeight: 500, textDecoration: "none" }}>
        R3VP
      </Link>
      {crumbs.map((crumb) => (
        <span key={crumb.href} style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ color: c.border, fontSize: 10 }}>›</span>
          {crumb.isLast ? (
            <span style={{ color: c.content, fontWeight: 600 }}>{crumb.label}</span>
          ) : (
            <Link href={crumb.href as Route} style={{ color: c.muted, fontWeight: 500, textDecoration: "none" }}>
              {crumb.label}
            </Link>
          )}
        </span>
      ))}
    </nav>
  );
}

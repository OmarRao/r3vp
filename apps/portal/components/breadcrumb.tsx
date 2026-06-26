"use client";

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

  return (
    <nav
      aria-label="Breadcrumb"
      style={{
        flexShrink: 0, background: "#F8FAFC", borderBottom: "1px solid #E2E8F0",
        padding: "0 28px", height: 32, display: "flex", alignItems: "center",
        gap: 6, fontSize: 11,
      }}
    >
      <Link href="/dashboard" style={{ color: "#64748B", fontWeight: 500, textDecoration: "none" }}>
        R3VP
      </Link>
      {crumbs.map((crumb) => (
        <span key={crumb.href} style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ color: "#CBD5E1", fontSize: 10 }}>›</span>
          {crumb.isLast ? (
            <span style={{ color: "#0F172A", fontWeight: 600 }}>{crumb.label}</span>
          ) : (
            <Link href={crumb.href} style={{ color: "#64748B", fontWeight: 500, textDecoration: "none" }}>
              {crumb.label}
            </Link>
          )}
        </span>
      ))}
    </nav>
  );
}

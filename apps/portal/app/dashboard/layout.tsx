import type { ReactNode } from "react";
import { Breadcrumb } from "@/components/breadcrumb";

const NAV_ITEMS = [
  { section: "Overview", items: [
    { href: "/dashboard", label: "Dashboard" },
    { href: "/dashboard/workloads", label: "Workloads" },
    { href: "/dashboard/test-runs", label: "Test Runs" },
    { href: "/dashboard/appliances", label: "Appliances" },
  ]},
  { section: "Security", items: [
    { href: "/dashboard/threats", label: "Threat Scanner" },
    { href: "/dashboard/incidents", label: "Incidents" },
    { href: "/dashboard/continuous-validation", label: "Continuous Validation" },
  ]},
  { section: "Compliance", items: [
    { href: "/dashboard/reports", label: "Reports" },
    { href: "/dashboard/reports/schedule", label: "Scheduled Delivery" },
  ]},
  { section: "Operations", items: [
    { href: "/dashboard/runbooks", label: "DR Runbooks" },
    { href: "/dashboard/fleet", label: "Fleet" },
    { href: "/dashboard/mssp", label: "MSSP Console" },
    { href: "/dashboard/providers", label: "Providers" },
    { href: "/dashboard/insights", label: "AI Insights" },
    { href: "/dashboard/integrations", label: "Integrations" },
  ]},
  { section: "Settings", items: [
    { href: "/dashboard/settings/team", label: "Team" },
    { href: "/dashboard/settings", label: "Settings" },
  ]},
];

export default function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <div style={{ display: "flex", height: "100vh", fontFamily: "'Segoe UI', system-ui, -apple-system, sans-serif", overflow: "hidden" }}>
      {/* Sidebar */}
      <aside style={{ width: 220, flexShrink: 0, background: "#0F172A", display: "flex", flexDirection: "column", overflowY: "auto" }}>
        <div style={{ padding: "20px 18px 16px", borderBottom: "1px solid rgba(255,255,255,0.07)" }}>
          <div style={{ fontSize: 21, fontWeight: 800, color: "#fff", letterSpacing: "-0.5px" }}>
            R<span style={{ color: "#00B336" }}>3</span>VP
          </div>
          <div style={{ fontSize: 9, color: "#00B336", textTransform: "uppercase", letterSpacing: "2px", marginTop: 2 }}>
            Recovery Validation
          </div>
        </div>
        <nav style={{ flex: 1, padding: "8px 0" }}>
          {NAV_ITEMS.map((section) => (
            <div key={section.section}>
              <div style={{ fontSize: 9, fontWeight: 700, textTransform: "uppercase", letterSpacing: "1.5px", color: "rgba(255,255,255,0.25)", padding: "12px 18px 4px" }}>
                {section.section}
              </div>
              {section.items.map((item) => (
                <a key={item.href} href={item.href} style={{ display: "flex", alignItems: "center", padding: "7px 18px", fontSize: 12, color: "rgba(255,255,255,0.6)", textDecoration: "none", borderLeft: "2px solid transparent" }}>
                  {item.label}
                </a>
              ))}
            </div>
          ))}
        </nav>
        <div style={{ padding: "12px 18px", borderTop: "1px solid rgba(255,255,255,0.07)", fontSize: 10, color: "rgba(255,255,255,0.25)", lineHeight: 1.7 }}>
          Built by Omar Rao
        </div>
      </aside>

      {/* Content area */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", minWidth: 0 }}>
        <Breadcrumb />
        <main style={{ flex: 1, overflowY: "auto", background: "#F8FAFC" }}>
          {children}
        </main>
      </div>
    </div>
  );
}

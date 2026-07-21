"use client";

import type { Route } from "next";
import Link from "next/link";
import { usePathname } from "next/navigation";

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

/**
 * Dashboard sidebar. The sidebar is intentionally dark navy in BOTH themes
 * (it is a fixed brand chrome element), so its colors are expressed as
 * white-opacity utilities rather than the theme tokens. Active/hover states
 * use the veeam green accent so they stay visible on the dark background.
 */
export function DashboardSidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-[220px] flex-shrink-0 bg-[#0F172A] flex flex-col overflow-y-auto">
      <div className="px-[18px] pt-5 pb-4 border-b border-white/[0.07]">
        <div className="text-[21px] font-extrabold text-white tracking-[-0.5px]">
          R<span className="text-[#00B336]">3</span>VP
        </div>
        <div className="text-[9px] text-[#00B336] uppercase tracking-[2px] mt-0.5">
          Recovery Validation
        </div>
      </div>
      <nav className="flex-1 py-2">
        {NAV_ITEMS.map((section) => (
          <div key={section.section}>
            <div className="text-[9px] font-bold uppercase tracking-[1.5px] text-white/25 px-[18px] pt-3 pb-1">
              {section.section}
            </div>
            {section.items.map((item) => {
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href as Route}
                  aria-current={active ? "page" : undefined}
                  className={`flex items-center px-[18px] py-[7px] text-xs no-underline border-l-2 transition-colors ${
                    active
                      ? "border-[#00B336] bg-white/[0.06] text-white font-semibold"
                      : "border-transparent text-white/60 hover:bg-white/[0.04] hover:text-white"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>
      <div className="px-[18px] py-3 border-t border-white/[0.07] text-[10px] text-white/25 leading-[1.7]">
        Built by Omar Rao
      </div>
    </aside>
  );
}

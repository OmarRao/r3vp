import type { ReactNode } from "react";
import { Breadcrumb } from "@/components/breadcrumb";
import { DashboardSidebar } from "@/components/dashboard-sidebar";
import { ThemeToggle } from "@/components/theme-toggle";

export default function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar (intentionally dark navy in both themes) */}
      <DashboardSidebar />

      {/* Content area */}
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        {/* Topbar: houses the theme toggle so it is reachable from every dashboard page */}
        <header className="flex-shrink-0 flex items-center justify-end gap-3 h-12 px-7 bg-surface border-b border-border">
          <ThemeToggle />
        </header>
        <Breadcrumb />
        <main className="flex-1 overflow-y-auto bg-bg">
          {children}
        </main>
      </div>
    </div>
  );
}

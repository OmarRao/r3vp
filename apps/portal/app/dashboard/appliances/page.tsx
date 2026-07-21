"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api";

interface Appliance {
  id: string;
  name: string;
  version: string | null;
  status: string;
  last_heartbeat: string | null;
  mtls_thumbprint: string;
  workload_count: number;
  created_at: string;
}

function applianceStatus(lastHeartbeat: string | null): "active" | "stale" | "offline" {
  if (!lastHeartbeat) return "offline";
  const mins = (Date.now() - new Date(lastHeartbeat).getTime()) / 60000;
  if (mins < 5) return "active";
  if (mins < 30) return "stale";
  return "offline";
}

function relativeTime(ts: string | null): string {
  if (!ts) return "Never";
  const mins = Math.floor((Date.now() - new Date(ts).getTime()) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs} hour${hrs > 1 ? "s" : ""} ago`;
  return `${Math.floor(hrs / 24)} day${Math.floor(hrs / 24) > 1 ? "s" : ""} ago`;
}

const statusBadgeClass: Record<string, string> = {
  active: "bg-green-100 text-green-800",
  stale: "bg-yellow-100 text-yellow-800",
  offline: "bg-red-100 text-red-800",
};

const statusLabel: Record<string, string> = {
  active: "Active",
  stale: "Stale",
  offline: "Offline",
};

export default function AppliancesPage() {
  const { data: appliances = [], isLoading } = useQuery<Appliance[]>({
    queryKey: ["portal-appliances"],
    queryFn: () => api.get("/v1/portal/appliances").then((r) => r.data),
  });

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold text-content">Appliances</h1>

      <div className="bg-surface rounded-xl shadow p-5">
        {isLoading ? (
          <div className="flex items-center gap-2 py-4">
            <div className="animate-spin border-4 rounded-full w-6 h-6 border-green-500 border-t-transparent" />
            <span className="text-sm text-content-muted">Loading appliances...</span>
          </div>
        ) : appliances.length === 0 ? (
          <p className="text-sm text-content-muted">No appliances registered yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b text-left text-content-muted text-xs uppercase tracking-wide">
                  <th className="pb-2 pr-4">Name</th>
                  <th className="pb-2 pr-4">Version</th>
                  <th className="pb-2 pr-4">Status</th>
                  <th className="pb-2 pr-4">Last Heartbeat</th>
                  <th className="pb-2 pr-4">Workloads</th>
                  <th className="pb-2 pr-4">Registered</th>
                  <th className="pb-2">Action</th>
                </tr>
              </thead>
              <tbody>
                {appliances.map((a) => {
                  const s = applianceStatus(a.last_heartbeat);
                  return (
                    <tr key={a.id} className="border-b hover:bg-surface-2">
                      <td className="py-2 pr-4 font-medium text-content">{a.name}</td>
                      <td className="py-2 pr-4 text-content-muted">{a.version ?? "—"}</td>
                      <td className="py-2 pr-4">
                        <span
                          className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusBadgeClass[s]}`}
                        >
                          {statusLabel[s]}
                        </span>
                      </td>
                      <td className="py-2 pr-4 text-content-muted text-xs">
                        {relativeTime(a.last_heartbeat)}
                      </td>
                      <td className="py-2 pr-4 text-content-muted">{a.workload_count}</td>
                      <td className="py-2 pr-4 text-content-muted text-xs">
                        {new Date(a.created_at).toLocaleDateString()}
                      </td>
                      <td className="py-2">
                        <Link
                          href={`/dashboard/appliances/${a.id}`}
                          className="text-veeam-green hover:underline text-xs font-medium"
                        >
                          View Details
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <p className="text-xs text-content-muted text-center pt-2">
        Built by{" "}
        <a
          href="https://www.linkedin.com/in/omarrao/"
          target="_blank"
          rel="noopener noreferrer"
          className="text-veeam-green hover:underline"
        >
          Omar Rao
        </a>
        , Engineer - Data Resilience, Cybersecurity and Privacy
      </p>
    </div>
  );
}

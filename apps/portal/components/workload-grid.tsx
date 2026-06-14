"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

type WorkloadStatus = "passed" | "failed" | "pending" | "never";

interface Workload {
  id: string;
  name: string;
  platform: string;
  os_type: string | null;
  is_protected: boolean;
  rto_target_mins: number | null;
  rpo_target_mins: number | null;
  last_test_run_status: WorkloadStatus | null;
  last_test_run_at: string | null;
}

const statusBadge: Record<string, string> = {
  passed: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
  pending: "bg-yellow-100 text-yellow-800",
  never: "bg-gray-100 text-gray-500",
};

export function WorkloadGrid() {
  const { data: workloads = [], isLoading } = useQuery<Workload[]>({
    queryKey: ["workloads"],
    queryFn: () => api.get("/v1/workloads").then((r) => r.data),
  });

  if (isLoading) return <p className="text-sm text-gray-400">Loading…</p>;
  if (!workloads.length)
    return <p className="text-sm text-gray-400">No workloads discovered yet.</p>;

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b text-left text-gray-500 text-xs uppercase tracking-wide">
            <th className="pb-2 pr-4">Name</th>
            <th className="pb-2 pr-4">Platform</th>
            <th className="pb-2 pr-4">Protected</th>
            <th className="pb-2 pr-4">RTO Target</th>
            <th className="pb-2 pr-4">RPO Target</th>
            <th className="pb-2 pr-4">Last Test</th>
            <th className="pb-2">Status</th>
          </tr>
        </thead>
        <tbody>
          {workloads.map((w) => {
            const status = w.last_test_run_status ?? "never";
            return (
              <tr key={w.id} className="border-b hover:bg-gray-50 cursor-pointer">
                <td className="py-2 pr-4 font-medium text-gray-900">{w.name}</td>
                <td className="py-2 pr-4 text-gray-600">{w.platform}</td>
                <td className="py-2 pr-4">
                  {w.is_protected ? (
                    <span className="text-green-600">✓</span>
                  ) : (
                    <span className="text-red-500">✗</span>
                  )}
                </td>
                <td className="py-2 pr-4 text-gray-600">
                  {w.rto_target_mins != null ? `${w.rto_target_mins} min` : "—"}
                </td>
                <td className="py-2 pr-4 text-gray-600">
                  {w.rpo_target_mins != null ? `${w.rpo_target_mins} min` : "—"}
                </td>
                <td className="py-2 pr-4 text-gray-500 text-xs">
                  {w.last_test_run_at
                    ? new Date(w.last_test_run_at).toLocaleDateString()
                    : "Never"}
                </td>
                <td className="py-2">
                  <span
                    className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusBadge[status] ?? statusBadge.never}`}
                  >
                    {status}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
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
  never: "bg-surface-2 text-content-muted",
};

export function WorkloadGrid() {
  const router = useRouter();
  const { data: workloads = [], isLoading } = useQuery<Workload[]>({
    queryKey: ["workloads"],
    queryFn: () => api.get("/v1/workloads").then((r) => r.data),
  });

  if (isLoading) return <p className="text-sm text-content-muted">Loading…</p>;
  if (!workloads.length)
    return <p className="text-sm text-content-muted">No workloads discovered yet.</p>;

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b text-left text-content-muted text-xs uppercase tracking-wide">
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
              <tr key={w.id} className="border-b hover:bg-surface-2 cursor-pointer" onClick={() => router.push(`/dashboard/workloads/${w.id}`)}>
                <td className="py-2 pr-4 font-medium text-content">{w.name}</td>
                <td className="py-2 pr-4 text-content-muted">{w.platform}</td>
                <td className="py-2 pr-4">
                  {w.is_protected ? (
                    <span className="text-green-600">✓</span>
                  ) : (
                    <span className="text-red-500">✗</span>
                  )}
                </td>
                <td className="py-2 pr-4 text-content-muted">
                  {w.rto_target_mins != null ? `${w.rto_target_mins} min` : "—"}
                </td>
                <td className="py-2 pr-4 text-content-muted">
                  {w.rpo_target_mins != null ? `${w.rpo_target_mins} min` : "—"}
                </td>
                <td className="py-2 pr-4 text-content-muted text-xs">
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

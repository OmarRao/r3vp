"use client";

import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";

interface Workload {
  id: string;
  name: string;
  platform: string;
  os_type: string | null;
  is_protected: boolean;
  rto_target_mins: number | null;
  rpo_target_mins: number | null;
  last_test_run_status: string | null;
  last_test_run_at: string | null;
  last_backup_at: string | null;
}

interface TestRunHistoryItem {
  id: string;
  started_at: string;
  status: "passed" | "failed" | "running" | "pending";
  actual_rto_mins: number | null;
  actual_rpo_mins: number | null;
  readiness_score: number | null;
}

interface TestRunCreated {
  id: string;
}

const statusBadge: Record<string, string> = {
  passed: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
  running: "bg-blue-100 text-blue-800",
  pending: "bg-yellow-100 text-yellow-800",
  never: "bg-gray-100 text-gray-500",
};

export default function WorkloadDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const { data: workload, isLoading } = useQuery<Workload>({
    queryKey: ["workload", id],
    queryFn: () => api.get(`/v1/workloads/${id}`).then((r) => r.data),
  });

  const { data: history = [], isLoading: historyLoading } = useQuery<TestRunHistoryItem[]>({
    queryKey: ["workload-history", id],
    queryFn: () => api.get(`/v1/workloads/${id}/history`).then((r) => r.data),
  });

  const [rtoInput, setRtoInput] = useState<string>("");
  const [rpoInput, setRpoInput] = useState<string>("");
  const [targetsSaved, setTargetsSaved] = useState(false);

  // Pre-fill inputs once workload loads
  const rtoValue = rtoInput !== "" ? rtoInput : (workload?.rto_target_mins?.toString() ?? "");
  const rpoValue = rpoInput !== "" ? rpoInput : (workload?.rpo_target_mins?.toString() ?? "");

  const runTestMutation = useMutation({
    mutationFn: () => api.post<TestRunCreated>("/v1/test-runs", { workload_id: id }).then((r) => r.data),
    onSuccess: (run) => {
      router.push(`/dashboard/test-runs/${run.id}`);
    },
  });

  const saveTargetsMutation = useMutation({
    mutationFn: () =>
      api.put(`/v1/workloads/${id}/targets`, {
        rto_target_mins: rtoValue ? Number(rtoValue) : null,
        rpo_target_mins: rpoValue ? Number(rpoValue) : null,
      }),
    onSuccess: () => {
      setTargetsSaved(true);
      setTimeout(() => setTargetsSaved(false), 3000);
    },
  });

  if (isLoading) {
    return (
      <div className="p-6 flex items-center justify-center">
        <div className="animate-spin border-4 rounded-full w-8 h-8 border-green-500 border-t-transparent" />
      </div>
    );
  }

  if (!workload) {
    return (
      <div className="p-6">
        <p className="text-gray-500">Workload not found.</p>
        <Link href="/dashboard" className="text-veeam-green text-sm mt-2 inline-block">
          &larr; Back to Workloads
        </Link>
      </div>
    );
  }

  const lastStatus = workload.last_test_run_status ?? "never";

  return (
    <div className="p-6 space-y-6">
      {/* Back link */}
      <Link href="/dashboard" className="text-sm text-veeam-green hover:underline">
        &larr; Back to Workloads
      </Link>

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-2xl font-bold text-gray-900">{workload.name}</h1>
          <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
            {workload.platform}
          </span>
          <span
            className={`px-2 py-0.5 rounded-full text-xs font-medium ${
              workload.is_protected ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"
            }`}
          >
            {workload.is_protected ? "Protected" : "Unprotected"}
          </span>
          <span
            className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusBadge[lastStatus] ?? statusBadge.never}`}
          >
            {lastStatus}
          </span>
        </div>
        <button
          onClick={() => runTestMutation.mutate()}
          disabled={runTestMutation.isPending}
          className="bg-veeam-green text-white px-4 py-2 rounded-lg font-medium hover:bg-green-700 disabled:opacity-60 transition-colors"
        >
          {runTestMutation.isPending ? "Starting..." : "Run Test Now"}
        </button>
      </div>

      {runTestMutation.isError && (
        <p className="text-sm text-red-600">Failed to start test run. Please try again.</p>
      )}

      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl shadow p-5">
          <p className="text-xs text-gray-500 uppercase tracking-wide">RTO Target</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">
            {workload.rto_target_mins != null ? `${workload.rto_target_mins} min` : "—"}
          </p>
        </div>
        <div className="bg-white rounded-xl shadow p-5">
          <p className="text-xs text-gray-500 uppercase tracking-wide">RPO Target</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">
            {workload.rpo_target_mins != null ? `${workload.rpo_target_mins} min` : "—"}
          </p>
        </div>
        <div className="bg-white rounded-xl shadow p-5">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Last Backup</p>
          <p className="text-lg font-semibold text-gray-900 mt-1">
            {workload.last_backup_at
              ? new Date(workload.last_backup_at).toLocaleString()
              : "—"}
          </p>
        </div>
        <div className="bg-white rounded-xl shadow p-5">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Status</p>
          <div className="mt-2">
            <span
              className={`px-2 py-0.5 rounded-full text-sm font-medium ${statusBadge[lastStatus] ?? statusBadge.never}`}
            >
              {lastStatus}
            </span>
          </div>
        </div>
      </div>

      {/* Set Targets form */}
      <div className="bg-white rounded-xl shadow p-5">
        <h2 className="text-lg font-semibold mb-4">Set Targets</h2>
        <div className="flex flex-wrap gap-4 items-end">
          <div>
            <label className="block text-sm text-gray-600 mb-1">RTO Target (mins)</label>
            <input
              type="number"
              min={0}
              value={rtoValue}
              onChange={(e) => setRtoInput(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm w-36 focus:outline-none focus:ring-2 focus:ring-veeam-green"
              placeholder="e.g. 60"
            />
          </div>
          <div>
            <label className="block text-sm text-gray-600 mb-1">RPO Target (mins)</label>
            <input
              type="number"
              min={0}
              value={rpoValue}
              onChange={(e) => setRpoInput(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm w-36 focus:outline-none focus:ring-2 focus:ring-veeam-green"
              placeholder="e.g. 15"
            />
          </div>
          <button
            onClick={() => saveTargetsMutation.mutate()}
            disabled={saveTargetsMutation.isPending}
            className="bg-veeam-green text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-60 transition-colors"
          >
            {saveTargetsMutation.isPending ? "Saving..." : "Save"}
          </button>
          {targetsSaved && (
            <span className="text-sm text-green-600 font-medium">Saved!</span>
          )}
          {saveTargetsMutation.isError && (
            <span className="text-sm text-red-600">Save failed. Please try again.</span>
          )}
        </div>
      </div>

      {/* Test Run History */}
      <div className="bg-white rounded-xl shadow p-5">
        <h2 className="text-lg font-semibold mb-4">Test Run History</h2>
        {historyLoading ? (
          <p className="text-sm text-gray-400">Loading history...</p>
        ) : history.length === 0 ? (
          <p className="text-sm text-gray-400">No test runs yet. Click "Run Test Now" to start.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b text-left text-gray-500 text-xs uppercase tracking-wide">
                  <th className="pb-2 pr-4">Date</th>
                  <th className="pb-2 pr-4">Status</th>
                  <th className="pb-2 pr-4">Actual RTO</th>
                  <th className="pb-2 pr-4">Actual RPO</th>
                  <th className="pb-2 pr-4">Readiness Score</th>
                  <th className="pb-2">Action</th>
                </tr>
              </thead>
              <tbody>
                {history.map((run) => (
                  <tr key={run.id} className="border-b hover:bg-gray-50">
                    <td className="py-2 pr-4 text-gray-600">
                      {new Date(run.started_at).toLocaleString()}
                    </td>
                    <td className="py-2 pr-4">
                      <span
                        className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusBadge[run.status] ?? statusBadge.never}`}
                      >
                        {run.status}
                      </span>
                    </td>
                    <td className="py-2 pr-4 text-gray-600">
                      {run.actual_rto_mins != null ? `${run.actual_rto_mins} min` : "—"}
                    </td>
                    <td className="py-2 pr-4 text-gray-600">
                      {run.actual_rpo_mins != null ? `${run.actual_rpo_mins} min` : "—"}
                    </td>
                    <td className="py-2 pr-4 text-gray-600">
                      {run.readiness_score != null ? run.readiness_score : "—"}
                    </td>
                    <td className="py-2">
                      <Link
                        href={`/dashboard/test-runs/${run.id}`}
                        className="text-veeam-green hover:underline text-xs font-medium"
                      >
                        View Details
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Footer attribution */}
      <p className="text-xs text-gray-400 text-center pt-2">
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

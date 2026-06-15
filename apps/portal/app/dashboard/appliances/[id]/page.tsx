"use client";

import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";

interface ApplianceDetail {
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

export default function ApplianceDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [copied, setCopied] = useState(false);
  const [deregisterError, setDeregisterError] = useState<string | null>(null);

  const { data: appliance, isLoading } = useQuery<ApplianceDetail>({
    queryKey: ["portal-appliance", id],
    queryFn: () => api.get(`/v1/portal/appliances/${id}`).then((r) => r.data),
  });

  const deregisterMutation = useMutation({
    mutationFn: () => api.delete(`/v1/portal/appliances/${id}`),
    onSuccess: () => {
      router.push("/dashboard/appliances");
    },
    onError: () => setDeregisterError("Failed to deregister appliance. Please try again."),
  });

  const handleCopy = () => {
    if (appliance) {
      navigator.clipboard.writeText(appliance.mtls_thumbprint).then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      });
    }
  };

  const handleDeregister = () => {
    if (window.confirm("Are you sure?")) {
      setDeregisterError(null);
      deregisterMutation.mutate();
    }
  };

  if (isLoading) {
    return (
      <div className="p-6 flex items-center gap-3">
        <div className="animate-spin border-4 rounded-full w-8 h-8 border-green-500 border-t-transparent" />
        <span className="text-sm text-gray-400">Loading appliance...</span>
      </div>
    );
  }

  if (!appliance) {
    return (
      <div className="p-6">
        <p className="text-gray-500">Appliance not found.</p>
        <Link href="/dashboard/appliances" className="text-veeam-green text-sm mt-2 inline-block">
          &larr; Back to Appliances
        </Link>
      </div>
    );
  }

  const s = applianceStatus(appliance.last_heartbeat);

  return (
    <div className="p-6 space-y-6">
      {/* Back link */}
      <Link href="/dashboard/appliances" className="text-sm text-veeam-green hover:underline">
        &larr; Back to Appliances
      </Link>

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-2xl font-bold text-gray-900">{appliance.name}</h1>
          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusBadgeClass[s]}`}>
            {statusLabel[s]}
          </span>
        </div>
        <p className="text-sm text-gray-400">
          Registered {new Date(appliance.created_at).toLocaleDateString()}
        </p>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl shadow p-5">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Version</p>
          <p className="text-xl font-bold text-gray-900 mt-1">{appliance.version ?? "—"}</p>
        </div>
        <div className="bg-white rounded-xl shadow p-5">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Status</p>
          <div className="mt-2">
            <span className={`px-2 py-0.5 rounded-full text-sm font-medium ${statusBadgeClass[s]}`}>
              {statusLabel[s]}
            </span>
          </div>
        </div>
        <div className="bg-white rounded-xl shadow p-5">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Last Heartbeat</p>
          <p className="text-lg font-semibold text-gray-900 mt-1">
            {relativeTime(appliance.last_heartbeat)}
          </p>
        </div>
        <div className="bg-white rounded-xl shadow p-5">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Workload Count</p>
          <p className="text-2xl font-bold text-gray-900 mt-1">{appliance.workload_count}</p>
        </div>
      </div>

      {/* Connection Info */}
      <div className="bg-white rounded-xl shadow p-5 space-y-4">
        <h2 className="text-lg font-semibold text-gray-900">Connection Info</h2>
        <div>
          <label className="block text-xs text-gray-500 uppercase tracking-wide mb-1">
            Appliance ID
          </label>
          <p className="font-mono text-sm text-gray-800 bg-gray-50 border border-gray-200 rounded px-3 py-2">
            {appliance.id}
          </p>
        </div>
        <div>
          <label className="block text-xs text-gray-500 uppercase tracking-wide mb-1">
            mTLS Thumbprint
          </label>
          <div className="flex items-center gap-2">
            <p className="font-mono text-sm text-gray-800 bg-gray-50 border border-gray-200 rounded px-3 py-2 flex-1 break-all">
              {appliance.mtls_thumbprint}
            </p>
            <button
              onClick={handleCopy}
              className="shrink-0 border border-gray-300 rounded-lg px-3 py-2 text-xs text-gray-600 hover:bg-gray-50 transition-colors"
            >
              {copied ? "Copied!" : "Copy"}
            </button>
          </div>
        </div>
      </div>

      {/* Workloads */}
      <div className="bg-white rounded-xl shadow p-5">
        <h2 className="text-lg font-semibold text-gray-900 mb-2">Workloads</h2>
        {appliance.workload_count > 0 ? (
          <Link
            href={`/dashboard?appliance=${appliance.id}`}
            className="text-veeam-green hover:underline text-sm font-medium"
          >
            View {appliance.workload_count} workload{appliance.workload_count !== 1 ? "s" : ""}
          </Link>
        ) : (
          <p className="text-sm text-gray-400">No workloads associated with this appliance.</p>
        )}
      </div>

      {/* Deregister */}
      <div className="bg-white rounded-xl shadow p-5 space-y-3">
        <h2 className="text-lg font-semibold text-gray-900">Deregister Appliance</h2>
        <p className="text-sm text-gray-500">
          This marks the appliance as deregistered. Existing workload records are preserved.
        </p>
        <button
          onClick={handleDeregister}
          disabled={deregisterMutation.isPending}
          className="bg-red-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-red-700 disabled:opacity-60 transition-colors"
        >
          {deregisterMutation.isPending ? "Deregistering..." : "Deregister"}
        </button>
        {deregisterError && (
          <p className="text-sm text-red-600">{deregisterError}</p>
        )}
      </div>

      {/* Footer */}
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

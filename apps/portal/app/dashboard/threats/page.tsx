"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

interface ThreatFinding {
  id: string;
  threat_name: string;
  threat_type: string;
  severity: string;
  host: string;
  indicator_type: string;
  indicator_value: string;
  mitre_technique: string | null;
  status: string;
  detected_at: string;
}

interface ThreatScan {
  id: string;
  scan_id: string;
  started_at: string;
  completed_at: string;
  hosts_scanned: number;
  signatures_checked: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
}

const severityBadge: Record<string, string> = {
  critical: "bg-red-100 text-red-800",
  high: "bg-orange-100 text-orange-800",
  medium: "bg-yellow-100 text-yellow-800",
  low: "bg-green-100 text-green-800",
};

const statusBadge: Record<string, string> = {
  active: "bg-red-100 text-red-700",
  investigating: "bg-blue-100 text-blue-700",
  resolved: "bg-green-100 text-green-700",
};

const typeBadge: Record<string, string> = {
  ransomware: "bg-red-50 text-red-600",
  malware: "bg-orange-50 text-orange-600",
  apt: "bg-purple-50 text-purple-600",
  cve: "bg-yellow-50 text-yellow-700",
  yara: "bg-blue-50 text-blue-600",
};

export default function ThreatsPage() {
  const qc = useQueryClient();

  const { data: findings = [], isLoading: findingsLoading } = useQuery<ThreatFinding[]>({
    queryKey: ["threat-findings"],
    queryFn: () => api.get("/v1/threat-intel/findings").then((r) => r.data),
  });

  const { data: scans = [] } = useQuery<ThreatScan[]>({
    queryKey: ["threat-scans"],
    queryFn: () => api.get("/v1/threat-intel/scans").then((r) => r.data),
  });

  const latestScan = scans[0];
  const criticalCount = findings.filter((f) => f.severity === "critical").length;
  const highCount = findings.filter((f) => f.severity === "high").length;
  const activeCount = findings.filter((f) => f.status === "active").length;

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Threat Scanner</h1>
          <p className="text-sm text-gray-500 mt-1">
            {latestScan
              ? `Last scan: ${new Date(latestScan.completed_at).toLocaleString()} -- ${latestScan.signatures_checked.toLocaleString()} signatures checked`
              : "No scans yet"}
          </p>
        </div>
        <button
          className="bg-red-600 text-white px-4 py-2 rounded-lg font-medium hover:bg-red-700 transition-colors text-sm"
          onClick={() => qc.invalidateQueries({ queryKey: ["threat-findings"] })}
        >
          Refresh Findings
        </button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl shadow p-5">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Critical</p>
          <p className="text-3xl font-bold text-red-600 mt-1">{criticalCount}</p>
        </div>
        <div className="bg-white rounded-xl shadow p-5">
          <p className="text-xs text-gray-500 uppercase tracking-wide">High</p>
          <p className="text-3xl font-bold text-orange-500 mt-1">{highCount}</p>
        </div>
        <div className="bg-white rounded-xl shadow p-5">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Active</p>
          <p className="text-3xl font-bold text-gray-900 mt-1">{activeCount}</p>
        </div>
        <div className="bg-white rounded-xl shadow p-5">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Total Findings</p>
          <p className="text-3xl font-bold text-gray-900 mt-1">{findings.length}</p>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow p-5">
        <h2 className="text-lg font-semibold mb-4">Findings</h2>
        {findingsLoading ? (
          <p className="text-sm text-gray-400">Loading findings...</p>
        ) : findings.length === 0 ? (
          <p className="text-sm text-gray-400">No threat findings. Environment is clean.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b text-left text-gray-500 text-xs uppercase tracking-wide">
                  <th className="pb-2 pr-4">Severity</th>
                  <th className="pb-2 pr-4">Threat</th>
                  <th className="pb-2 pr-4">Type</th>
                  <th className="pb-2 pr-4">Host</th>
                  <th className="pb-2 pr-4">Indicator</th>
                  <th className="pb-2 pr-4">MITRE</th>
                  <th className="pb-2 pr-4">Detected</th>
                  <th className="pb-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {findings.map((f) => (
                  <tr key={f.id} className="border-b hover:bg-gray-50">
                    <td className="py-2 pr-4">
                      <span
                        className={`px-2 py-0.5 rounded text-xs font-bold uppercase ${
                          severityBadge[f.severity] ?? "bg-gray-100 text-gray-600"
                        }`}
                      >
                        {f.severity}
                      </span>
                    </td>
                    <td className="py-2 pr-4 font-medium text-gray-900">{f.threat_name}</td>
                    <td className="py-2 pr-4">
                      <span
                        className={`px-2 py-0.5 rounded text-xs font-medium ${
                          typeBadge[f.threat_type] ?? "bg-gray-100 text-gray-600"
                        }`}
                      >
                        {f.threat_type}
                      </span>
                    </td>
                    <td className="py-2 pr-4 text-gray-600 font-mono text-xs">{f.host}</td>
                    <td className="py-2 pr-4 text-gray-500 text-xs">
                      <span className="text-gray-400">{f.indicator_type}:</span>{" "}
                      <span className="font-mono">
                        {f.indicator_value.length > 30
                          ? f.indicator_value.slice(0, 30) + "..."
                          : f.indicator_value}
                      </span>
                    </td>
                    <td className="py-2 pr-4 text-gray-500 text-xs font-mono">
                      {f.mitre_technique ?? "—"}
                    </td>
                    <td className="py-2 pr-4 text-gray-500 text-xs">
                      {new Date(f.detected_at).toLocaleString()}
                    </td>
                    <td className="py-2">
                      <span
                        className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                          statusBadge[f.status] ?? "bg-gray-100 text-gray-600"
                        }`}
                      >
                        {f.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

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

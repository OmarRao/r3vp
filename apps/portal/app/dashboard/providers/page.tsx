"use client";
/*
 * Copyright (c) 2026 Omar Rao
 * SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
 * This file is available under the GNU Affero General Public License v3.0
 * or under a separate commercial license.
 */


import { useQuery } from "@tanstack/react-query";
import type { Route } from "next";
import Link from "next/link";
import { api } from "@/lib/api";

interface ProviderSummary {
  provider: string;
  total_workloads: number;
  total_runs: number;
  pass_rate: number | null;
  avg_rto_mins: number | null;
}

const providerMeta: Record<string, { label: string; color: string; bg: string; icon: string; border: string }> = {
  vmware:    { label: "VMware vSphere",   color: "text-blue-700",    bg: "bg-blue-50",    icon: "VM",  border: "border-blue-600"    },
  hyperv:    { label: "Hyper-V",          color: "text-purple-700",  bg: "bg-purple-50",  icon: "HV",  border: "border-purple-600"  },
  azure:     { label: "Azure Backup",     color: "text-sky-700",     bg: "bg-sky-50",     icon: "AZ",  border: "border-sky-500"     },
  aws:       { label: "AWS Backup",       color: "text-orange-700",  bg: "bg-orange-50",  icon: "AWS", border: "border-orange-500"  },
  proxmox:   { label: "Proxmox VE",       color: "text-orange-700",  bg: "bg-orange-50",  icon: "PVE", border: "border-orange-400"  },
  nutanix:   { label: "Nutanix AHV",      color: "text-red-800",     bg: "bg-red-50",     icon: "NTX", border: "border-red-800"     },
  rhv:       { label: "RHV / oVirt",      color: "text-red-700",     bg: "bg-red-50",     icon: "RHV", border: "border-red-600"     },
  xenserver: { label: "XenServer",        color: "text-teal-700",    bg: "bg-teal-50",    icon: "XEN", border: "border-teal-600"    },
  sangfor:   { label: "Sangfor HCI",      color: "text-blue-800",    bg: "bg-blue-50",    icon: "SF",  border: "border-blue-700"    },
  gcp:       { label: "Google Cloud",     color: "text-blue-700",    bg: "bg-blue-50",    icon: "GCP", border: "border-blue-500"    },
};

function PassRateBar({ rate }: { rate: number | null }) {
  if (rate === null) {
    return <span className="text-xs text-content-muted">No runs yet</span>;
  }
  const color = rate >= 80 ? "bg-green-500" : rate >= 50 ? "bg-yellow-400" : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-surface-2 rounded-full h-2">
        <div className={`${color} h-2 rounded-full`} style={{ width: `${rate}%` }} />
      </div>
      <span className="text-xs font-semibold text-content w-8 text-right">{rate}%</span>
    </div>
  );
}

export default function ProvidersPage() {
  const { data: providers = [], isLoading } = useQuery<ProviderSummary[]>({
    queryKey: ["provider-summary"],
    queryFn: () => api.get("/v1/multicloud/provider-summary").then((r) => r.data),
  });

  const totalWorkloads = providers.reduce((s, p) => s + p.total_workloads, 0);
  const totalRuns = providers.reduce((s, p) => s + p.total_runs, 0);

  return (
    <div className="p-6 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-content">Multi-Cloud Providers</h1>
          <p className="text-sm text-content-muted mt-1">
            {totalWorkloads} workloads across {providers.filter((p) => p.total_workloads > 0).length} providers &bull; {totalRuns} recovery tests total
          </p>
        </div>
        <Link
          href="/dashboard"
          className="text-sm text-veeam-green hover:underline"
        >
          &larr; Back to Dashboard
        </Link>
      </div>

      {isLoading && (
        <div className="flex justify-center py-12">
          <div className="animate-spin border-4 rounded-full w-8 h-8 border-veeam-green border-t-transparent" />
        </div>
      )}

      {/* Provider cards: 2 cols on mobile, 3 cols on md+ */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-5">
        {providers.map((p) => {
          const meta = providerMeta[p.provider] ?? {
            label: p.provider,
            color: "text-content",
            bg: "bg-surface-2",
            icon: p.provider.slice(0, 3).toUpperCase(),
            border: "border-border",
          };
          const configured = p.total_workloads > 0;

          return (
            <div
              key={p.provider}
              className={`bg-surface rounded-xl shadow p-5 border-l-4 ${
                configured ? meta.border : "border-border"
              }`}
            >
              <div className="flex items-start gap-4">
                <div
                  className={`w-12 h-12 rounded-lg ${meta.bg} ${meta.color} flex items-center justify-center text-sm font-bold shrink-0`}
                >
                  {meta.icon}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    <h2 className="text-base font-bold text-content">{meta.label}</h2>
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                        configured
                          ? "bg-green-100 text-green-700"
                          : "bg-surface-2 text-content-muted"
                      }`}
                    >
                      {configured ? "Active" : "Not configured"}
                    </span>
                  </div>

                  <div className="grid grid-cols-3 gap-3 mt-3">
                    <div>
                      <p className="text-xs text-content-muted uppercase tracking-wide">Workloads</p>
                      <p className="text-xl font-bold text-content mt-0.5">
                        {p.total_workloads}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-content-muted uppercase tracking-wide">Test Runs</p>
                      <p className="text-xl font-bold text-content mt-0.5">{p.total_runs}</p>
                    </div>
                    <div>
                      <p className="text-xs text-content-muted uppercase tracking-wide">Avg RTO</p>
                      <p className="text-xl font-bold text-content mt-0.5">
                        {p.avg_rto_mins != null ? `${p.avg_rto_mins}m` : "--"}
                      </p>
                    </div>
                  </div>

                  <div className="mt-3">
                    <p className="text-xs text-content-muted uppercase tracking-wide mb-1.5">
                      Pass Rate
                    </p>
                    <PassRateBar rate={p.pass_rate} />
                  </div>

                  {configured && (
                    <div className="mt-3">
                      <Link
                        href={`/dashboard/workloads?provider=${p.provider}` as Route}
                        className="text-xs text-veeam-green hover:underline font-medium"
                      >
                        View {p.total_workloads} workloads &rarr;
                      </Link>
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Veeam B&R version matrix */}
      <div className="bg-surface rounded-xl shadow p-5">
        <h2 className="text-lg font-semibold mb-4">Veeam B&amp;R API Version Matrix</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left border-collapse">
            <thead>
              <tr className="bg-surface-2 text-xs text-content-muted uppercase tracking-wide">
                <th className="px-3 py-2 border border-border">Veeam Version</th>
                <th className="px-3 py-2 border border-border">API Version</th>
                <th className="px-3 py-2 border border-border">Key Capabilities</th>
              </tr>
            </thead>
            <tbody className="text-content">
              <tr className="hover:bg-surface-2">
                <td className="px-3 py-2 border border-border font-medium">Veeam B&amp;R 11</td>
                <td className="px-3 py-2 border border-border font-mono text-xs">v1.0</td>
                <td className="px-3 py-2 border border-border">Job management, basic restore</td>
              </tr>
              <tr className="hover:bg-surface-2">
                <td className="px-3 py-2 border border-border font-medium">Veeam B&amp;R 12</td>
                <td className="px-3 py-2 border border-border font-mono text-xs">v1.1</td>
                <td className="px-3 py-2 border border-border">Instant VM recovery, object storage</td>
              </tr>
              <tr className="hover:bg-surface-2">
                <td className="px-3 py-2 border border-border font-medium">Veeam B&amp;R 13.0.2+</td>
                <td className="px-3 py-2 border border-border font-mono text-xs">v1.2</td>
                <td className="px-3 py-2 border border-border">Enhanced restore points, malware detection</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Extended hypervisor support matrix */}
      <div className="bg-surface rounded-xl shadow p-5">
        <h2 className="text-lg font-semibold mb-1">Extended Hypervisor Support Matrix</h2>
        <p className="text-xs text-content-muted mb-4">Phase 6 connector architecture for non-Veeam-native platforms</p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left border-collapse">
            <thead>
              <tr className="bg-surface-2 text-xs text-content-muted uppercase tracking-wide">
                <th className="px-3 py-2 border border-border">Platform</th>
                <th className="px-3 py-2 border border-border">Protocol</th>
                <th className="px-3 py-2 border border-border">Connector</th>
                <th className="px-3 py-2 border border-border">Backup Integration</th>
                <th className="px-3 py-2 border border-border">Notes</th>
              </tr>
            </thead>
            <tbody className="text-content">
              <tr className="hover:bg-surface-2">
                <td className="px-3 py-2 border border-border font-medium">Proxmox VE</td>
                <td className="px-3 py-2 border border-border font-mono text-xs">REST API</td>
                <td className="px-3 py-2 border border-border font-mono text-xs">proxmoxer</td>
                <td className="px-3 py-2 border border-border">PBS (Proxmox Backup Server)</td>
                <td className="px-3 py-2 border border-border text-content-muted">Native snapshot support</td>
              </tr>
              <tr className="hover:bg-surface-2">
                <td className="px-3 py-2 border border-border font-medium">Nutanix AHV</td>
                <td className="px-3 py-2 border border-border font-mono text-xs">Prism Central v3 REST</td>
                <td className="px-3 py-2 border border-border font-mono text-xs">httpx</td>
                <td className="px-3 py-2 border border-border">Protection Domains</td>
                <td className="px-3 py-2 border border-border text-content-muted">No SDK dependency</td>
              </tr>
              <tr className="hover:bg-surface-2">
                <td className="px-3 py-2 border border-border font-medium">RHV / oVirt</td>
                <td className="px-3 py-2 border border-border font-mono text-xs">oVirt SDK</td>
                <td className="px-3 py-2 border border-border font-mono text-xs">ovirt-engine-sdk-python</td>
                <td className="px-3 py-2 border border-border">Export domains</td>
                <td className="px-3 py-2 border border-border text-content-muted">Manual SDK install</td>
              </tr>
              <tr className="hover:bg-surface-2">
                <td className="px-3 py-2 border border-border font-medium">XenServer</td>
                <td className="px-3 py-2 border border-border font-mono text-xs">XenAPI (XML-RPC)</td>
                <td className="px-3 py-2 border border-border font-mono text-xs">XenAPI module</td>
                <td className="px-3 py-2 border border-border">XenServer Backup</td>
                <td className="px-3 py-2 border border-border text-content-muted">Manual SDK install</td>
              </tr>
              <tr className="hover:bg-surface-2">
                <td className="px-3 py-2 border border-border font-medium">Sangfor HCI</td>
                <td className="px-3 py-2 border border-border font-mono text-xs">REST API</td>
                <td className="px-3 py-2 border border-border font-mono text-xs">httpx</td>
                <td className="px-3 py-2 border border-border">Vendor snapshots</td>
                <td className="px-3 py-2 border border-border text-content-muted">Requires vendor API spec</td>
              </tr>
              <tr className="hover:bg-surface-2">
                <td className="px-3 py-2 border border-border font-medium">Google Cloud</td>
                <td className="px-3 py-2 border border-border font-mono text-xs">Compute API</td>
                <td className="px-3 py-2 border border-border font-mono text-xs">google-cloud-compute</td>
                <td className="px-3 py-2 border border-border">GCP Backup and DR</td>
                <td className="px-3 py-2 border border-border text-content-muted">ADC / Service Account</td>
              </tr>
            </tbody>
          </table>
        </div>
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

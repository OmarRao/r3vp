"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api";

interface ProviderSummary {
  provider: string;
  total_workloads: number;
  total_runs: number;
  pass_rate: number | null;
  avg_rto_mins: number | null;
}

const providerMeta: Record<string, { label: string; color: string; bg: string; icon: string }> = {
  vmware: { label: "VMware vSphere", color: "text-blue-700", bg: "bg-blue-50", icon: "VM" },
  hyperv: { label: "Hyper-V", color: "text-purple-700", bg: "bg-purple-50", icon: "HV" },
  azure: { label: "Azure Backup", color: "text-sky-700", bg: "bg-sky-50", icon: "AZ" },
  aws: { label: "AWS Backup", color: "text-orange-700", bg: "bg-orange-50", icon: "AWS" },
};

function PassRateBar({ rate }: { rate: number | null }) {
  if (rate === null) {
    return <span className="text-xs text-gray-400">No runs yet</span>;
  }
  const color = rate >= 80 ? "bg-green-500" : rate >= 50 ? "bg-yellow-400" : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-gray-100 rounded-full h-2">
        <div className={`${color} h-2 rounded-full`} style={{ width: `${rate}%` }} />
      </div>
      <span className="text-xs font-semibold text-gray-700 w-8 text-right">{rate}%</span>
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
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Multi-Cloud Providers</h1>
          <p className="text-sm text-gray-500 mt-1">
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

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {providers.map((p) => {
          const meta = providerMeta[p.provider] ?? {
            label: p.provider,
            color: "text-gray-700",
            bg: "bg-gray-50",
            icon: p.provider.slice(0, 3).toUpperCase(),
          };
          const configured = p.total_workloads > 0;

          return (
            <div
              key={p.provider}
              className={`bg-white rounded-xl shadow p-5 border-l-4 ${
                configured ? "border-veeam-green" : "border-gray-200"
              }`}
            >
              <div className="flex items-start gap-4">
                <div
                  className={`w-12 h-12 rounded-lg ${meta.bg} ${meta.color} flex items-center justify-center text-sm font-bold shrink-0`}
                >
                  {meta.icon}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <h2 className="text-base font-bold text-gray-900">{meta.label}</h2>
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                        configured
                          ? "bg-green-100 text-green-700"
                          : "bg-gray-100 text-gray-500"
                      }`}
                    >
                      {configured ? "Active" : "Not configured"}
                    </span>
                  </div>

                  <div className="grid grid-cols-3 gap-3 mt-3">
                    <div>
                      <p className="text-xs text-gray-400 uppercase tracking-wide">Workloads</p>
                      <p className="text-xl font-bold text-gray-900 mt-0.5">
                        {p.total_workloads}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-400 uppercase tracking-wide">Test Runs</p>
                      <p className="text-xl font-bold text-gray-900 mt-0.5">{p.total_runs}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-400 uppercase tracking-wide">Avg RTO</p>
                      <p className="text-xl font-bold text-gray-900 mt-0.5">
                        {p.avg_rto_mins != null ? `${p.avg_rto_mins}m` : "--"}
                      </p>
                    </div>
                  </div>

                  <div className="mt-3">
                    <p className="text-xs text-gray-400 uppercase tracking-wide mb-1.5">
                      Pass Rate
                    </p>
                    <PassRateBar rate={p.pass_rate} />
                  </div>

                  {configured && (
                    <div className="mt-3">
                      <Link
                        href={`/dashboard/workloads?provider=${p.provider}`}
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

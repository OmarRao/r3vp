"use client";

import { useQuery } from "@tanstack/react-query";
import { ReadinessGauge } from "@/components/readiness-gauge";
import { RtoRpoChart } from "@/components/rto-rpo-chart";
import { WorkloadGrid } from "@/components/workload-grid";
import { api } from "@/lib/api";

export default function DashboardPage() {
  const { data: readiness } = useQuery({
    queryKey: ["readiness"],
    queryFn: () => api.get("/v1/dashboard/readiness").then((r) => r.data),
  });

  const { data: coverage } = useQuery({
    queryKey: ["coverage"],
    queryFn: () => api.get("/v1/dashboard/coverage").then((r) => r.data),
  });

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Recovery Readiness Dashboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl shadow p-5 flex flex-col items-center">
          <ReadinessGauge score={readiness?.overall_score ?? 0} />
          <p className="mt-2 text-sm text-gray-500">Overall Readiness Score</p>
        </div>

        <div className="bg-white rounded-xl shadow p-5">
          <p className="text-xs text-gray-500 uppercase tracking-wide">Workloads Tested</p>
          <p className="text-4xl font-bold text-veeam-green mt-1">
            {readiness?.workloads_tested ?? 0}
            <span className="text-xl text-gray-400"> / {readiness?.workloads_total ?? 0}</span>
          </p>
          <p className="text-sm text-gray-500 mt-1">in last 30 days</p>
        </div>

        <div className="bg-white rounded-xl shadow p-5 space-y-2">
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wide">RTO Compliance</p>
            <p className="text-3xl font-bold text-gray-800">
              {readiness?.rto_compliance_pct ?? 0}%
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wide">RPO Compliance</p>
            <p className="text-3xl font-bold text-gray-800">
              {readiness?.rpo_compliance_pct ?? 0}%
            </p>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow p-5">
        <h2 className="text-lg font-semibold mb-4">RTO / RPO Trend (last 90 days)</h2>
        <RtoRpoChart data={readiness?.trend ?? []} />
      </div>

      <div className="bg-white rounded-xl shadow p-5">
        <h2 className="text-lg font-semibold mb-4">Workloads</h2>
        <WorkloadGrid />
      </div>
    </div>
  );
}

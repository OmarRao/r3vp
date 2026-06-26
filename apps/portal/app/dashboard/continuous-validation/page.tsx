"use client";

const ALERTS = [
  {
    id: "a1",
    workload: "files-prod-01",
    type: "consecutive_failures",
    severity: "high",
    detail: "3 consecutive micro-validation failures. Last Veeam job failed with E0x8019.",
    time: "Jun 26 13:45",
  },
  {
    id: "a2",
    workload: "erp-prod-01",
    type: "restore_point_stale",
    severity: "medium",
    detail: "Restore point age 6h exceeds RPO target of 4h.",
    time: "Jun 26 14:00",
  },
];

const RUNS = [
  { workload: "db-prod-01", status: "pass", checks: "4/4", rp: "1h", ms: 312 },
  { workload: "dc-prod-02", status: "pass", checks: "4/4", rp: "2h", ms: 289 },
  { workload: "erp-prod-01", status: "warn", checks: "3/4", rp: "6h", ms: 445 },
  { workload: "files-prod-01", status: "fail", checks: "2/4", rp: "18h", ms: 580 },
];

const CHECKS = [
  { name: "Restore Point Freshness", desc: "Verifies the latest restore point is within the RPO window" },
  { name: "Mount Endpoint Reachability", desc: "Tests that the recovery mount endpoint responds within 5s" },
  { name: "Veeam Job Status", desc: "Checks last backup job completed with Success or Warning" },
  { name: "Appliance Heartbeat", desc: "Confirms appliance heartbeat within last interval" },
  { name: "vCenter Connectivity", desc: "Verifies appliance can reach vCenter and enumerate the protected VM" },
  { name: "RPO Compliance Check", desc: "Calculates current RPO exposure vs the workload RPO target" },
];

const statusPill = (s: string) =>
  s === "pass"
    ? "bg-green-50 text-green-700 border-green-200"
    : s === "warn"
    ? "bg-amber-50 text-amber-700 border-amber-200"
    : "bg-red-50 text-red-700 border-red-200";

export default function ContinuousValidationPage() {
  return (
    <div className="p-7 bg-slate-50 min-h-screen">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Continuous Validation</h1>
          <p className="text-sm text-slate-400 mt-1">
            Always-on micro-checks running every 15 minutes without full instant recovery
          </p>
        </div>
        <button className="px-4 py-2 bg-green-500 hover:bg-green-600 text-white text-sm font-semibold rounded-md">
          + New Policy
        </button>
      </div>

      {/* Health Summary KPIs */}
      <div className="grid grid-cols-4 gap-4 mb-5">
        {[
          { label: "Overall Status", value: "Healthy", color: "text-green-600" },
          { label: "Pass Rate (24h)", value: "94%", color: "text-green-600" },
          { label: "Active Alerts", value: "2", color: "text-amber-500" },
          { label: "Checks Today", value: "1,847", color: "text-slate-900" },
        ].map((k) => (
          <div key={k.label} className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm text-center">
            <div className={`text-2xl font-bold ${k.color} mb-1`}>{k.value}</div>
            <div className="text-xs text-slate-400">{k.label}</div>
          </div>
        ))}
      </div>

      {/* Policies */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden mb-5">
        <div className="px-5 py-3.5 border-b border-slate-100">
          <span className="text-sm font-bold text-slate-900">Validation Policies (2)</span>
        </div>
        {[
          { name: "Production Workloads", interval: "Every 15 min", scope: "All workloads", checks: "Restore Point, Mount, Veeam Job, Heartbeat" },
          { name: "Critical Tier Only", interval: "Every 5 min", scope: "tag:critical", checks: "All 6 checks" },
        ].map((p, i) => (
          <div key={i} className="flex items-center gap-4 px-5 py-3.5 border-b border-slate-50 last:border-0">
            <div className="w-8 h-4 rounded-full flex-shrink-0 relative cursor-pointer bg-green-500">
              <span className="absolute top-0.5 left-4 w-3 h-3 bg-white rounded-full shadow" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-slate-900">
                {p.name}{" "}
                <span className="text-xs font-normal text-slate-400 ml-2">{p.interval}</span>
              </p>
              <p className="text-xs text-slate-400 mt-0.5">
                Scope: {p.scope} &nbsp;&middot;&nbsp; Checks: {p.checks}
              </p>
            </div>
            <button className="text-xs text-slate-400 hover:text-green-600 font-semibold border border-slate-200 rounded px-2 py-1">
              Edit
            </button>
          </div>
        ))}
      </div>

      {/* Active Alerts */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden mb-5">
        <div className="px-5 py-3.5 border-b border-slate-100">
          <span className="text-sm font-bold text-slate-900">Active Alerts ({ALERTS.length})</span>
        </div>
        {ALERTS.map((a) => (
          <div
            key={a.id}
            className={`flex items-start gap-4 px-5 py-4 border-b border-slate-50 last:border-0 border-l-4 ${
              a.severity === "high" ? "border-l-red-500" : "border-l-amber-400"
            }`}
          >
            <span
              className={`text-xs font-bold uppercase px-2 py-0.5 rounded border flex-shrink-0 ${
                a.severity === "high"
                  ? "bg-red-50 text-red-700 border-red-200"
                  : "bg-amber-50 text-amber-700 border-amber-200"
              }`}
            >
              {a.severity}
            </span>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-slate-900 mb-0.5">
                {a.workload}{" "}
                <span className="font-normal text-slate-400 text-xs ml-1">{a.type}</span>
              </p>
              <p className="text-xs text-slate-500">{a.detail}</p>
            </div>
            <div className="text-xs text-slate-400 whitespace-nowrap">{a.time}</div>
            <button className="text-xs text-slate-400 hover:text-green-600 font-semibold border border-slate-200 rounded px-2 py-1 whitespace-nowrap">
              Resolve
            </button>
          </div>
        ))}
      </div>

      {/* Recent Checks Table */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden mb-5">
        <div className="px-5 py-3.5 border-b border-slate-100">
          <span className="text-sm font-bold text-slate-900">Recent Micro-Validation Runs</span>
        </div>
        <table className="w-full">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-100">
              {["Workload", "Status", "Checks", "RP Age", "Duration", "Time"].map((h) => (
                <th key={h} className="text-[10px] font-bold uppercase tracking-wide text-slate-400 px-5 py-2.5 text-left">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {RUNS.map((r) => (
              <tr key={r.workload} className="border-b border-slate-50 hover:bg-slate-50">
                <td className="px-5 py-3 text-sm font-medium text-slate-900">{r.workload}</td>
                <td className="px-5 py-3">
                  <span className={`text-[10px] font-bold uppercase border rounded px-2 py-0.5 ${statusPill(r.status)}`}>
                    {r.status}
                  </span>
                </td>
                <td className="px-5 py-3 text-sm text-slate-600">{r.checks}</td>
                <td className="px-5 py-3 text-sm text-slate-600">{r.rp}</td>
                <td className="px-5 py-3 text-sm text-slate-500">{r.ms}ms</td>
                <td className="px-5 py-3 text-sm text-slate-400">14:00</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Available Checks */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        <div className="px-5 py-3.5 border-b border-slate-100">
          <span className="text-sm font-bold text-slate-900">Available Micro-Checks</span>
        </div>
        <div className="p-4 grid grid-cols-2 gap-3">
          {CHECKS.map((c) => (
            <div key={c.name} className="flex items-start gap-3 p-3 border border-slate-100 rounded-lg">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="flex-shrink-0 mt-0.5">
                <path d="M3 8l3 3 7-7" stroke="#00B336" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              <div>
                <p className="text-xs font-semibold text-slate-900">{c.name}</p>
                <p className="text-[11px] text-slate-400 mt-0.5">{c.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

"use client";
import { useState } from "react";

const SCENARIO_COLORS: Record<string, string> = {
  ransomware: "bg-red-100 text-red-800 border-red-200",
  datacenter_failure: "bg-amber-100 text-amber-800 border-amber-200",
  cloud_outage: "bg-blue-100 text-blue-800 border-blue-200",
  site_failover: "bg-purple-100 text-purple-800 border-purple-200",
  custom: "bg-slate-100 text-slate-600 border-slate-200",
};

const STATUS_COLORS: Record<string, string> = {
  completed: "bg-green-50 text-green-700 border-green-200",
  failed: "bg-red-50 text-red-700 border-red-200",
  running: "bg-blue-50 text-blue-700 border-blue-200",
  pending: "bg-slate-50 text-slate-500 border-slate-200",
  rolled_back: "bg-amber-50 text-amber-700 border-amber-200",
};

const MOCK_RUNBOOKS = [
  { id: "r1", name: "Full Ransomware Recovery", scenario: "ransomware", rto_target_mins: 240, tags: ["critical", "production"], step_count: 12, waves: 4, est_mins: 200, last_status: "completed", last_rto: 187, last_run: "Jun 22" },
  { id: "r2", name: "DC-East Failover", scenario: "datacenter_failure", rto_target_mins: 180, tags: ["tier-1", "east-coast"], step_count: 8, waves: 3, est_mins: 130, last_status: "completed", last_rto: 162, last_run: "Jun 15" },
  { id: "r3", name: "Azure Region Failover", scenario: "cloud_outage", rto_target_mins: 120, tags: ["azure", "production"], step_count: 6, waves: 2, est_mins: 90, last_status: null, last_rto: null, last_run: null },
  { id: "r4", name: "NYC to DR Site", scenario: "site_failover", rto_target_mins: 240, tags: ["site-failover", "nyc"], step_count: 10, waves: 3, est_mins: 165, last_status: "failed", last_rto: null, last_run: "May 28" },
];

const MOCK_EXECUTIONS = [
  { runbook: "Full Ransomware Recovery", trigger: "Manual", started: "Jun 22 14:00", duration: 187, target: 240, status: "completed", rto_met: true },
  { runbook: "DC-East Failover", trigger: "Manual", started: "Jun 15 09:30", duration: 162, target: 180, status: "completed", rto_met: true },
  { runbook: "NYC to DR Site", trigger: "Scheduled", started: "May 28 02:00", duration: null, target: 240, status: "failed", rto_met: false },
  { runbook: "Full Ransomware Recovery", trigger: "Manual", started: "May 10 11:00", duration: 201, target: 240, status: "completed", rto_met: true },
];

export default function RunbooksPage() {
  const [filter, setFilter] = useState("all");
  const scenarios = ["all", "ransomware", "datacenter_failure", "cloud_outage", "site_failover", "custom"];
  const filtered = filter === "all" ? MOCK_RUNBOOKS : MOCK_RUNBOOKS.filter(r => r.scenario === filter);

  return (
    <div className="p-7 bg-slate-50 min-h-screen">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-start justify-between mb-6">
          <div>
            <h1 className="text-xl font-bold text-slate-900">DR Runbooks</h1>
            <p className="text-sm text-slate-400 mt-1">Structured recovery playbooks for ransomware, site failover, and cloud outage scenarios</p>
          </div>
          <button className="px-4 py-2 bg-green-500 hover:bg-green-600 text-white text-sm font-semibold rounded-md">+ New Runbook</button>
        </div>

        <div className="flex gap-2 mb-5 flex-wrap">
          {scenarios.map(s => (
            <button key={s} onClick={() => setFilter(s)}
              className={`px-3 py-1.5 text-xs font-semibold rounded-full border capitalize transition-colors ${filter === s ? "bg-green-500 text-white border-green-500" : "bg-white text-slate-500 border-slate-200 hover:border-green-400"}`}>
              {s.replace("_", " ")}
            </button>
          ))}
        </div>

        <div className="grid grid-cols-2 gap-4 mb-6">
          {filtered.map(r => (
            <div key={r.id} className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <span className={`text-[10px] font-bold uppercase tracking-wide border px-2 py-0.5 rounded mr-2 ${SCENARIO_COLORS[r.scenario]}`}>
                    {r.scenario.replace("_", " ")}
                  </span>
                  <span className="inline-block w-2 h-2 rounded-full bg-green-400 ml-1" />
                </div>
              </div>
              <h3 className="font-bold text-slate-900 text-base mb-2">{r.name}</h3>
              <div className="flex gap-1.5 mb-3 flex-wrap">
                {r.tags.map(t => <span key={t} className="text-[10px] bg-slate-100 text-slate-500 px-2 py-0.5 rounded">#{t}</span>)}
              </div>
              <div className="text-xs text-slate-500 mb-1">{r.step_count} steps &middot; {r.waves} waves &middot; Est. {Math.floor(r.est_mins/60)}h {r.est_mins%60}m</div>
              <div className="text-xs text-slate-500 mb-3">RTO target: {r.rto_target_mins} min</div>
              {r.last_run ? (
                <div className="text-xs mb-3">
                  Last run: {r.last_run} &middot;{" "}
                  <span className={`font-semibold ${r.last_status === "completed" ? "text-green-600" : "text-red-600"}`}>
                    {r.last_status === "completed" ? `${r.last_rto} min` : "Failed"}
                  </span>
                  {r.last_status === "completed" && r.last_rto && r.last_rto <= r.rto_target_mins && (
                    <span className="ml-1 text-[10px] font-bold text-green-700 bg-green-50 border border-green-200 px-1.5 py-0.5 rounded">RTO MET</span>
                  )}
                </div>
              ) : (
                <div className="text-xs text-slate-400 mb-3">Never executed</div>
              )}
              <div className="flex gap-2">
                <button className="flex-1 py-1.5 text-xs font-semibold text-slate-600 border border-slate-200 rounded hover:bg-slate-50">View</button>
                <button className="flex-1 py-1.5 text-xs font-semibold text-white bg-green-500 hover:bg-green-600 rounded">Execute</button>
              </div>
            </div>
          ))}
        </div>

        <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
          <div className="px-5 py-3.5 border-b border-slate-100">
            <span className="text-sm font-bold text-slate-900">Execution History</span>
          </div>
          <table className="w-full">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-100">
                {["Runbook", "Trigger", "Started", "Duration", "RTO Target", "Status"].map(h => (
                  <th key={h} className="text-[10px] font-bold uppercase tracking-wide text-slate-400 px-5 py-2.5 text-left">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {MOCK_EXECUTIONS.map((e, i) => (
                <tr key={i} className="border-b border-slate-50 hover:bg-slate-50">
                  <td className="px-5 py-3 text-sm font-medium text-slate-900">{e.runbook}</td>
                  <td className="px-5 py-3 text-sm text-slate-500">{e.trigger}</td>
                  <td className="px-5 py-3 text-xs text-slate-400">{e.started}</td>
                  <td className="px-5 py-3 text-sm text-slate-700">{e.duration ? `${e.duration} min` : "-"}</td>
                  <td className="px-5 py-3 text-sm text-slate-500">{e.target} min</td>
                  <td className="px-5 py-3 flex items-center gap-1.5">
                    <span className={`text-xs font-bold border px-2 py-0.5 rounded uppercase ${STATUS_COLORS[e.status]}`}>{e.status}</span>
                    {e.rto_met && <span className="text-[10px] font-bold text-green-700 bg-green-50 border border-green-200 px-1.5 py-0.5 rounded">RTO MET</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

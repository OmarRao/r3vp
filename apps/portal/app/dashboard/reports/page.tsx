"use client";
import { useState } from "react";

const FRAMEWORKS = [
  { id: "soc2", label: "SOC 2 Type II", controls: "CC7.5, CC9.1, A1.3", color: "#2563EB" },
  { id: "iso27001", label: "ISO 27001:2022", controls: "A.8.13, A.8.14, A.5.29, A.5.30", color: "#7C3AED" },
  { id: "nist_csf", label: "NIST CSF 2.0", controls: "RC.RP-01, RC.RP-02, RC.RP-05", color: "#0891B2" },
  { id: "monthly_summary", label: "Monthly Summary", controls: "All workloads", color: "#00B336" },
  { id: "cyber_insurance", label: "Cyber Insurance", controls: "Full evidence bundle", color: "#D97706" },
];

const MOCK_HISTORY = [
  { id: "a1b2", report_type: "soc2", from_date: "2026-05-01", to_date: "2026-05-31", generated_at: "2026-06-01T09:00:00Z", status: "ready", summary: { pass_rate_pct: 88, rto_compliance_pct: 85, controls_passing: 3, controls_total: 3, total_runs: 91 } },
  { id: "c3d4", report_type: "iso27001", from_date: "2026-05-01", to_date: "2026-05-31", generated_at: "2026-06-01T09:02:00Z", status: "ready", summary: { pass_rate_pct: 88, rto_compliance_pct: 85, controls_passing: 4, controls_total: 4, total_runs: 91 } },
  { id: "e5f6", report_type: "monthly_summary", from_date: "2026-05-01", to_date: "2026-05-31", generated_at: "2026-06-01T09:05:00Z", status: "ready", summary: { pass_rate_pct: 88, rto_compliance_pct: 85, total_runs: 172 } },
  { id: "g7h8", report_type: "nist_csf", from_date: "2026-04-01", to_date: "2026-04-30", generated_at: "2026-05-01T09:00:00Z", status: "ready", summary: { pass_rate_pct: 82, rto_compliance_pct: 80, controls_passing: 4, controls_total: 4, total_runs: 78 } },
];

export default function ReportsPage() {
  const [fromDate, setFromDate] = useState("2026-05-01");
  const [toDate, setToDate] = useState("2026-05-31");
  const [selected, setSelected] = useState("soc2");
  const [generating, setGenerating] = useState(false);

  const fw = FRAMEWORKS.find(f => f.id === selected);

  return (
    <div className="p-7 bg-slate-50 min-h-screen">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="flex items-start justify-between mb-6">
          <div>
            <h1 className="text-xl font-bold text-slate-900">Compliance Reports</h1>
            <p className="text-sm text-slate-400 mt-1">Generate signed PDF evidence for SOC 2, ISO 27001, NIST CSF, and cyber insurance audits</p>
          </div>
        </div>

        {/* Generate section */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 mb-6 shadow-sm">
          <h2 className="text-sm font-bold text-slate-900 mb-4">Generate New Report</h2>
          {/* Framework selector */}
          <div className="grid grid-cols-5 gap-3 mb-5">
            {FRAMEWORKS.map(f => (
              <button
                key={f.id}
                onClick={() => setSelected(f.id)}
                className={`p-3 rounded-lg border text-left transition-all ${selected === f.id ? "border-green-400 bg-green-50 ring-1 ring-green-300" : "border-slate-200 hover:border-slate-300"}`}
              >
                <div className="text-xs font-bold text-slate-900 mb-1">{f.label}</div>
                <div className="text-[10px] text-slate-400">{f.controls}</div>
              </button>
            ))}
          </div>
          {/* Date range + generate */}
          <div className="flex items-end gap-4">
            <div>
              <label className="text-xs font-semibold text-slate-600 block mb-1">From</label>
              <input type="date" value={fromDate} onChange={e => setFromDate(e.target.value)} className="border border-slate-200 rounded-md px-3 py-2 text-sm text-slate-900 outline-none focus:border-green-400" />
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-600 block mb-1">To</label>
              <input type="date" value={toDate} onChange={e => setToDate(e.target.value)} className="border border-slate-200 rounded-md px-3 py-2 text-sm text-slate-900 outline-none focus:border-green-400" />
            </div>
            <button
              onClick={() => setGenerating(true)}
              disabled={generating}
              className="px-5 py-2 bg-green-500 hover:bg-green-600 text-white text-sm font-semibold rounded-md flex items-center gap-2 disabled:opacity-60"
            >
              {generating ? "Generating..." : "Generate PDF"}
            </button>
          </div>
          {fw && (
            <p className="text-xs text-slate-400 mt-3">
              Selected: <strong className="text-slate-600">{fw.label}</strong> covering controls {fw.controls}. Report will be SHA-256 signed and stored in your audit history.
            </p>
          )}
        </div>

        {/* History table */}
        <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
          <div className="px-5 py-3.5 border-b border-slate-100 flex items-center justify-between">
            <span className="text-sm font-bold text-slate-900">Report History</span>
            <span className="text-xs text-slate-400">{MOCK_HISTORY.length} reports</span>
          </div>
          <table className="w-full">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-100">
                <th className="text-[10px] font-bold uppercase tracking-wide text-slate-400 px-5 py-2.5 text-left">Framework</th>
                <th className="text-[10px] font-bold uppercase tracking-wide text-slate-400 px-4 py-2.5 text-left">Period</th>
                <th className="text-[10px] font-bold uppercase tracking-wide text-slate-400 px-4 py-2.5 text-left">Pass Rate</th>
                <th className="text-[10px] font-bold uppercase tracking-wide text-slate-400 px-4 py-2.5 text-left">RTO</th>
                <th className="text-[10px] font-bold uppercase tracking-wide text-slate-400 px-4 py-2.5 text-left">Controls</th>
                <th className="text-[10px] font-bold uppercase tracking-wide text-slate-400 px-4 py-2.5 text-left">Generated</th>
                <th className="text-[10px] font-bold uppercase tracking-wide text-slate-400 px-4 py-2.5 text-left">Actions</th>
              </tr>
            </thead>
            <tbody>
              {MOCK_HISTORY.map(r => (
                <tr key={r.id} className="border-b border-slate-50 hover:bg-slate-50">
                  <td className="px-5 py-3">
                    <span className="text-xs font-bold text-blue-700 bg-blue-50 border border-blue-100 px-2 py-0.5 rounded">
                      {FRAMEWORKS.find(f => f.id === r.report_type)?.label ?? r.report_type}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-600">{r.from_date} to {r.to_date}</td>
                  <td className="px-4 py-3 text-sm font-bold text-green-700">{r.summary.pass_rate_pct}%</td>
                  <td className="px-4 py-3 text-sm font-bold text-green-700">{r.summary.rto_compliance_pct}%</td>
                  <td className="px-4 py-3 text-xs text-slate-600">
                    {r.summary.controls_passing != null ? `${r.summary.controls_passing}/${r.summary.controls_total} passing` : `${r.summary.total_runs} runs`}
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-400">{new Date(r.generated_at).toLocaleDateString()}</td>
                  <td className="px-4 py-3">
                    <button className="text-xs text-green-600 font-semibold hover:text-green-700 mr-3">Download</button>
                    <button className="text-xs text-slate-400 hover:text-slate-600">View</button>
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

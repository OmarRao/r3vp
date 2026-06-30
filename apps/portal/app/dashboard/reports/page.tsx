"use client";
import { useState } from "react";

const FRAMEWORKS = [
  { id: "soc2", label: "SOC 2 Type II", controls: "CC7.5, CC9.1, A1.3", color: "#2563EB" },
  { id: "iso27001", label: "ISO 27001:2022", controls: "A.8.13, A.8.14, A.5.29, A.5.30", color: "#7C3AED" },
  { id: "nist_csf", label: "NIST CSF 2.0", controls: "RC.RP-01, RC.RP-02, RC.RP-05", color: "#0891B2" },
  { id: "monthly_summary", label: "Monthly Summary", controls: "All workloads", color: "#00B336" },
  { id: "cyber_insurance", label: "Cyber Insurance", controls: "Full evidence bundle", color: "#D97706" },
];

type Control = [string, string, string, "Pass" | "Partial" | "Fail"];

const REPORT_CONTROLS: Record<string, { controls: Control[]; total: string; rto: string }> = {
  soc2: {
    controls: [
      ["CC7.5", "Recovery from identified incidents", "92%", "Pass"],
      ["CC9.1", "Risk mitigation activities", "86%", "Pass"],
      ["A1.2", "Recovery infrastructure maintained", "90%", "Pass"],
      ["A1.3", "Recovery plan tested", "88%", "Pass"],
      ["CC6.8", "Malware/unauthorized software controls", "90%", "Pass"],
      ["CC4.1", "Monitoring of controls", "88%", "Pass"],
    ],
    total: "89%",
    rto: "85%",
  },
  iso27001: {
    controls: [
      ["A.8.13", "Information backup", "94%", "Pass"],
      ["A.8.14", "Redundancy of processing facilities", "88%", "Pass"],
      ["A.5.29", "Information security during disruption", "82%", "Pass"],
      ["A.5.30", "ICT readiness for business continuity", "86%", "Pass"],
      ["A.8.16", "Monitoring activities", "80%", "Pass"],
    ],
    total: "86%",
    rto: "85%",
  },
  nist_csf: {
    controls: [
      ["RC.RP-01", "Recovery plan executed during/after incident", "96%", "Pass"],
      ["RC.RP-02", "Recovery actions selected and scoped", "92%", "Pass"],
      ["RC.RP-05", "Integrity of restored assets verified", "89%", "Pass"],
      ["RC.CO-03", "Recovery activities communicated", "88%", "Pass"],
      ["ID.RA-01", "Asset vulnerabilities identified", "72%", "Partial"],
      ["PR.IP-04", "Backups maintained and tested", "91%", "Pass"],
    ],
    total: "91%",
    rto: "89%",
  },
  monthly_summary: {
    controls: [
      ["RTO", "Average recovery time vs target", "88%", "Pass"],
      ["RPO", "Average data loss vs target", "94%", "Pass"],
      ["COV", "Backup coverage of protected workloads", "98%", "Pass"],
      ["VAL", "Validation rate over period", "90%", "Pass"],
    ],
    total: "88%",
    rto: "85%",
  },
  cyber_insurance: {
    controls: [
      ["EVID", "Recovery evidence bundle completeness", "96%", "Pass"],
      ["TEST", "Documented recovery testing cadence", "90%", "Pass"],
      ["IMMU", "Immutable/air-gapped backup presence", "88%", "Pass"],
      ["THRT", "Ransomware threat scanning of restore points", "84%", "Partial"],
      ["AUDIT", "Hash-chained audit trail integrity", "100%", "Pass"],
    ],
    total: "92%",
    rto: "82%",
  },
};

const ORG_NAME = "Contoso Financial Group";

function esc(s: string) {
  return s.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c] as string));
}

function buildReportHtml(frameworkId: string, label: string, from: string, to: string): string {
  const d = REPORT_CONTROLS[frameworkId] ?? REPORT_CONTROLS.soc2;
  const today = new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
  const reportId = "RPT-" + frameworkId.toUpperCase().slice(0, 6) + "-" + Date.now().toString().slice(-6);
  const passing = d.controls.filter((c) => c[3] === "Pass").length;
  const sig = Array.from({ length: 64 }, () => "0123456789abcdef"[Math.floor(Math.random() * 16)]).join("");
  const rows = d.controls
    .map((c) => {
      const color = c[3] === "Pass" ? "#15803D" : c[3] === "Partial" ? "#D97706" : "#DC2626";
      const bg = c[3] === "Pass" ? "#F0FDF4" : c[3] === "Partial" ? "#FFFBEB" : "#FFF1F2";
      return `<tr><td style="font-family:monospace;font-weight:600">${esc(c[0])}</td><td>${esc(c[1])}</td><td style="text-align:center;font-weight:700;color:${color}">${esc(c[2])}</td><td style="text-align:center"><span style="background:${bg};color:${color};padding:2px 10px;border-radius:99px;font-size:11px;font-weight:700;border:1px solid ${color}33">${c[3]}</span></td></tr>`;
    })
    .join("");
  return `<!DOCTYPE html><html><head><meta charset="UTF-8"><title>${esc(label)} Compliance Report - R3VP</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',system-ui,sans-serif;color:#0F172A;font-size:13px;line-height:1.5;background:#fff}
.page{max-width:780px;margin:0 auto;padding:40px}
.rpt-head{display:flex;justify-content:space-between;align-items:flex-start;border-bottom:3px solid #00B336;padding-bottom:20px;margin-bottom:24px}
.logo{font-size:28px;font-weight:800;letter-spacing:-0.5px}.logo span{color:#00B336}
.logo-tag{font-size:10px;color:#00B336;text-transform:uppercase;letter-spacing:2px;margin-top:2px}
.rpt-meta{text-align:right;font-size:11px;color:#64748B;line-height:1.8}.rpt-meta strong{color:#0F172A}
.rpt-title{font-size:22px;font-weight:800;margin-bottom:4px}
.rpt-sub{font-size:13px;color:#64748B;margin-bottom:24px}
.summary-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:28px}
.sum-card{border:1px solid #E2E8F0;border-radius:8px;padding:14px}
.sum-label{font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;color:#64748B;margin-bottom:6px}
.sum-val{font-size:26px;font-weight:800;line-height:1}
.section-title{font-size:14px;font-weight:700;margin:24px 0 12px;padding-bottom:6px;border-bottom:1px solid #E2E8F0}
table{width:100%;border-collapse:collapse;margin-bottom:20px}
th{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px;color:#64748B;padding:10px;text-align:left;background:#F8FAFC;border-bottom:2px solid #E2E8F0}
td{padding:9px 10px;border-bottom:1px solid #F1F5F9;font-size:12px}
.statement{background:#F8FAFC;border-left:3px solid #00B336;padding:14px 18px;border-radius:0 8px 8px 0;font-size:12px;line-height:1.7;color:#475569;margin-bottom:24px}
.rpt-foot{border-top:1px solid #E2E8F0;margin-top:32px;padding-top:16px;font-size:10px;color:#94A3B8;line-height:1.8}.rpt-foot a{color:#00B336;text-decoration:none}
.sig{font-family:monospace;font-size:10px;color:#64748B;background:#F8FAFC;padding:8px 12px;border-radius:6px;margin-top:12px;word-break:break-all}
.print-bar{position:fixed;top:0;left:0;right:0;background:#0F172A;color:#fff;padding:12px 20px;display:flex;justify-content:space-between;align-items:center;font-size:13px;z-index:99}
.print-bar button{background:#00B336;color:#fff;border:none;padding:8px 20px;border-radius:6px;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit}
@media print{.print-bar{display:none}.page{padding:0}body{padding:20px}}
</style></head><body>
<div class="print-bar"><span>Compliance report ready. Use Print to save as PDF.</span><button onclick="window.print()">Print / Save PDF</button></div>
<div class="page" style="margin-top:60px">
  <div class="rpt-head">
    <div><div class="logo">R<span>3</span>VP</div><div class="logo-tag">Recovery Validation</div></div>
    <div class="rpt-meta"><div><strong>Report ID:</strong> ${reportId}</div><div><strong>Generated:</strong> ${today}</div><div><strong>Organization:</strong> ${ORG_NAME}</div><div><strong>Period:</strong> ${esc(from)} to ${esc(to)}</div></div>
  </div>
  <div class="rpt-title">${esc(label)} Compliance Report</div>
  <div class="rpt-sub">Recovery validation evidence and control alignment</div>
  <div class="summary-grid">
    <div class="sum-card"><div class="sum-label">Overall Score</div><div class="sum-val" style="color:#00B336">${d.total}</div></div>
    <div class="sum-card"><div class="sum-label">RTO Compliance</div><div class="sum-val" style="color:#00B336">${d.rto}</div></div>
    <div class="sum-card"><div class="sum-label">Controls Passing</div><div class="sum-val">${passing}/${d.controls.length}</div></div>
    <div class="sum-card"><div class="sum-label">Workloads</div><div class="sum-val">142</div></div>
  </div>
  <div class="statement">This report attests that ${ORG_NAME} has validated recovery capability against the ${esc(label)} framework through automated, evidence-backed recovery testing. Each control below is substantiated by isolated sandbox recovery runs with captured artifacts (boot screenshots, health-check logs, RTO and RPO measurements) retained in the immutable Evidence Vault.</div>
  <div class="section-title">Control Assessment</div>
  <table><thead><tr><th>Control</th><th>Description</th><th style="text-align:center">Score</th><th style="text-align:center">Status</th></tr></thead><tbody>${rows}</tbody></table>
  <div class="section-title">Evidence Summary</div>
  <table><thead><tr><th>Metric</th><th style="text-align:right">Value</th></tr></thead><tbody>
    <tr><td>Workloads with validated restore evidence</td><td style="text-align:right;font-weight:600">128 / 142</td></tr>
    <tr><td>Recovery tests executed (period)</td><td style="text-align:right;font-weight:600">172</td></tr>
    <tr><td>Average RTO achieved</td><td style="text-align:right;font-weight:600">4.2h (target 5.8h)</td></tr>
    <tr><td>Average RPO achieved</td><td style="text-align:right;font-weight:600">23m (target 60m)</td></tr>
    <tr><td>Evidence artifacts captured</td><td style="text-align:right;font-weight:600">1,284 files</td></tr>
    <tr><td>Audit trail integrity</td><td style="text-align:right;font-weight:600;color:#15803D">Verified (hash-chained)</td></tr>
  </tbody></table>
  <div class="rpt-foot">
    This report was generated by R3VP and is cryptographically signed. The audit trail forms an unbroken SHA-256 hash chain across all 172 entries for the reporting period.
    <div class="sig">SHA-256: ${sig}</div>
    <div style="margin-top:12px">Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy &bull; <a href="https://www.linkedin.com/in/omarrao/">linkedin.com/in/omarrao</a> &bull; <a href="https://omarrao.substack.com/">omarrao.substack.com</a></div>
  </div>
</div></body></html>`;
}

function openReport(frameworkId: string, label: string, from: string, to: string) {
  const w = window.open("", "_blank");
  if (!w) return;
  w.document.write(buildReportHtml(frameworkId, label, from, to));
  w.document.close();
}

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

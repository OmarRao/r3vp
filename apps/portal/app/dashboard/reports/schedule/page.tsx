"use client";
import { useState } from "react";

const FRAMEWORKS = [
  { id: "soc2", label: "SOC 2 Type II" },
  { id: "iso27001", label: "ISO 27001:2022" },
  { id: "nist_csf", label: "NIST CSF 2.0" },
  { id: "monthly_summary", label: "Monthly Summary" },
  { id: "cyber_insurance", label: "Cyber Insurance" },
];

const CADENCES = [
  { id: "monthly", label: "Monthly", desc: "1st of each month at 08:00" },
  { id: "quarterly", label: "Quarterly", desc: "1st of Jan, Apr, Jul, Oct" },
  { id: "weekly", label: "Weekly", desc: "Every Monday at 08:00" },
];

const MOCK_SCHEDULES = [
  { id: "s1", name: "SOC 2 Monthly", report_type: "soc2", cron: "0 8 1 * *", period_days: 30, enabled: true, recipients: [{ type: "email", destination: "ciso@acmecorp.com" }, { type: "slack", destination: "#security" }], next_run_at: "2026-07-01T08:00:00Z", last_run_at: "2026-06-01T08:03:22Z" },
  { id: "s2", name: "ISO 27001 Quarterly", report_type: "iso27001", cron: "0 8 1 1,4,7,10 *", period_days: 90, enabled: true, recipients: [{ type: "email", destination: "audit@acmecorp.com" }], next_run_at: "2026-07-01T08:00:00Z", last_run_at: "2026-04-01T08:01:15Z" },
  { id: "s3", name: "Cyber Insurance Annual", report_type: "cyber_insurance", cron: "0 8 1 1 *", period_days: 365, enabled: false, recipients: [{ type: "email", destination: "insurance@acmecorp.com" }], next_run_at: null, last_run_at: "2026-01-01T08:00:00Z" },
];

export default function SchedulePage() {
  const [schedules, setSchedules] = useState(MOCK_SCHEDULES);
  const [showNew, setShowNew] = useState(false);
  const [form, setForm] = useState({ name: "", report_type: "soc2", cadence: "monthly", period_days: 30, recipient_type: "email", recipient_dest: "" });

  function toggleEnabled(id: string) {
    setSchedules(prev => prev.map(s => s.id === id ? { ...s, enabled: !s.enabled } : s));
  }

  function deleteSchedule(id: string) {
    setSchedules(prev => prev.filter(s => s.id !== id));
  }

  return (
    <div className="p-7 bg-slate-50 min-h-screen">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-start justify-between mb-6">
          <div>
            <h1 className="text-xl font-bold text-slate-900">Scheduled Delivery</h1>
            <p className="text-sm text-slate-400 mt-1">Automatically generate and deliver compliance reports on a recurring schedule</p>
          </div>
          <button onClick={() => setShowNew(true)} className="px-4 py-2 bg-green-500 hover:bg-green-600 text-white text-sm font-semibold rounded-md">
            + New Schedule
          </button>
        </div>

        {showNew && (
          <div className="bg-white border border-slate-200 rounded-xl p-6 mb-6 shadow-sm">
            <h2 className="text-sm font-bold text-slate-900 mb-4">New Schedule</h2>
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <label className="text-xs font-semibold text-slate-600 block mb-1">Schedule Name</label>
                <input value={form.name} onChange={e => setForm({...form, name: e.target.value})} placeholder="e.g. SOC 2 Monthly" className="w-full border border-slate-200 rounded-md px-3 py-2 text-sm outline-none focus:border-green-400" />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-600 block mb-1">Framework</label>
                <select value={form.report_type} onChange={e => setForm({...form, report_type: e.target.value})} className="w-full border border-slate-200 rounded-md px-3 py-2 text-sm outline-none focus:border-green-400 bg-white">
                  {FRAMEWORKS.map(f => <option key={f.id} value={f.id}>{f.label}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-600 block mb-1">Cadence</label>
                <select value={form.cadence} onChange={e => setForm({...form, cadence: e.target.value})} className="w-full border border-slate-200 rounded-md px-3 py-2 text-sm outline-none focus:border-green-400 bg-white">
                  {CADENCES.map(c => <option key={c.id} value={c.id}>{c.label} - {c.desc}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-600 block mb-1">Coverage Period (days)</label>
                <input type="number" value={form.period_days} onChange={e => setForm({...form, period_days: Number(e.target.value)})} className="w-full border border-slate-200 rounded-md px-3 py-2 text-sm outline-none focus:border-green-400" />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-600 block mb-1">Delivery Channel</label>
                <select value={form.recipient_type} onChange={e => setForm({...form, recipient_type: e.target.value})} className="w-full border border-slate-200 rounded-md px-3 py-2 text-sm outline-none focus:border-green-400 bg-white">
                  <option value="email">Email</option>
                  <option value="slack">Slack Webhook</option>
                  <option value="teams">Teams Webhook</option>
                </select>
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-600 block mb-1">Destination</label>
                <input value={form.recipient_dest} onChange={e => setForm({...form, recipient_dest: e.target.value})} placeholder={form.recipient_type === "email" ? "ciso@company.com" : "https://hooks.slack.com/..."} className="w-full border border-slate-200 rounded-md px-3 py-2 text-sm outline-none focus:border-green-400" />
              </div>
            </div>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setShowNew(false)} className="px-4 py-2 text-sm text-slate-500 border border-slate-200 rounded-md hover:bg-slate-50">Cancel</button>
              <button className="px-4 py-2 bg-green-500 hover:bg-green-600 text-white text-sm font-semibold rounded-md">Create Schedule</button>
            </div>
          </div>
        )}

        <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
          <div className="px-5 py-3.5 border-b border-slate-100 flex items-center justify-between">
            <span className="text-sm font-bold text-slate-900">Active Schedules</span>
            <span className="text-xs text-slate-400">{schedules.length} configured</span>
          </div>
          <table className="w-full">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-100">
                <th className="text-[10px] font-bold uppercase tracking-wide text-slate-400 px-5 py-2.5 text-left">Name</th>
                <th className="text-[10px] font-bold uppercase tracking-wide text-slate-400 px-4 py-2.5 text-left">Framework</th>
                <th className="text-[10px] font-bold uppercase tracking-wide text-slate-400 px-4 py-2.5 text-left">Schedule</th>
                <th className="text-[10px] font-bold uppercase tracking-wide text-slate-400 px-4 py-2.5 text-left">Recipients</th>
                <th className="text-[10px] font-bold uppercase tracking-wide text-slate-400 px-4 py-2.5 text-left">Last Run</th>
                <th className="text-[10px] font-bold uppercase tracking-wide text-slate-400 px-4 py-2.5 text-left">Next Run</th>
                <th className="text-[10px] font-bold uppercase tracking-wide text-slate-400 px-4 py-2.5 text-left">Status</th>
                <th className="text-[10px] font-bold uppercase tracking-wide text-slate-400 px-4 py-2.5 text-left">Actions</th>
              </tr>
            </thead>
            <tbody>
              {schedules.map(s => (
                <tr key={s.id} className="border-b border-slate-50 hover:bg-slate-50">
                  <td className="px-5 py-3 text-sm font-medium text-slate-900">{s.name}</td>
                  <td className="px-4 py-3"><span className="text-xs font-bold text-blue-700 bg-blue-50 border border-blue-100 px-2 py-0.5 rounded">{FRAMEWORKS.find(f => f.id === s.report_type)?.label}</span></td>
                  <td className="px-4 py-3 text-xs text-slate-500 font-mono">{s.cron}</td>
                  <td className="px-4 py-3 text-xs text-slate-500">{s.recipients.map(r => r.destination).join(", ")}</td>
                  <td className="px-4 py-3 text-xs text-slate-400">{s.last_run_at ? new Date(s.last_run_at).toLocaleDateString() : "Never"}</td>
                  <td className="px-4 py-3 text-xs text-slate-400">{s.next_run_at && s.enabled ? new Date(s.next_run_at).toLocaleDateString() : "-"}</td>
                  <td className="px-4 py-3">
                    {s.enabled
                      ? <span className="text-xs font-bold text-green-700 bg-green-50 border border-green-200 px-2 py-0.5 rounded-full">Active</span>
                      : <span className="text-xs font-bold text-slate-400 bg-slate-100 border border-slate-200 px-2 py-0.5 rounded-full">Paused</span>}
                  </td>
                  <td className="px-4 py-3 flex gap-2">
                    <button onClick={() => toggleEnabled(s.id)} className="text-xs text-slate-400 hover:text-green-600 font-semibold">{s.enabled ? "Pause" : "Resume"}</button>
                    <button onClick={() => deleteSchedule(s.id)} className="text-xs text-slate-400 hover:text-red-500 font-semibold">Delete</button>
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

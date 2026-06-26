"use client";
import { useState } from "react";

const CUSTOMERS = [
  { id: "c1", name: "Acme Corporation", industry: "Financial Services", tier: "premium", score: 87, workloads: 42, threats: 0, lastTest: "Today 14:22", status: "healthy" },
  { id: "c2", name: "Globex Industries", industry: "Manufacturing", tier: "standard", score: 61, workloads: 28, threats: 1, lastTest: "Jun 20", status: "warning" },
  { id: "c3", name: "Initech Solutions", industry: "Technology", tier: "enterprise", score: 94, workloads: 67, threats: 0, lastTest: "Today 09:15", status: "healthy" },
  { id: "c4", name: "Umbrella Medical", industry: "Healthcare", tier: "premium", score: 72, workloads: 35, threats: 0, lastTest: "Jun 22", status: "healthy" },
  { id: "c5", name: "Stark Logistics", industry: "Retail", tier: "standard", score: 38, workloads: 19, threats: 2, lastTest: "Jun 10", status: "critical" },
];

const scoreColor = (s: number) =>
  s >= 80 ? "text-green-600 bg-green-50" : s >= 60 ? "text-amber-600 bg-amber-50" : "text-red-600 bg-red-50";

const statusDot = (s: string) =>
  s === "healthy" ? "bg-green-500" : s === "warning" ? "bg-amber-400" : "bg-red-500";

const tierBadge = (t: string) =>
  t === "enterprise"
    ? "bg-blue-50 text-blue-700 border-blue-200"
    : t === "premium"
    ? "bg-purple-50 text-purple-700 border-purple-200"
    : "bg-slate-100 text-slate-600 border-slate-200";

export default function MsspPage() {
  const avg = Math.round(CUSTOMERS.reduce((s, c) => s + c.score, 0) / CUSTOMERS.length);

  return (
    <div className="p-7 bg-slate-50 min-h-screen">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-slate-900">MSSP Console</h1>
          <p className="text-sm text-slate-400 mt-1">Manage your customer organizations and cross-org readiness</p>
        </div>
        <button className="px-4 py-2 bg-green-500 hover:bg-green-600 text-white text-sm font-semibold rounded-md">
          + Add Customer
        </button>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-5 gap-4 mb-5">
        {[
          { label: "Total Customers", value: "5", color: "text-slate-900" },
          { label: "Healthy", value: "3", color: "text-green-600" },
          { label: "Warning", value: "1", color: "text-amber-500" },
          { label: "Critical", value: "1", color: "text-red-500" },
          { label: "Avg Readiness", value: `${avg}`, color: avg >= 80 ? "text-green-600" : "text-amber-500" },
        ].map((k) => (
          <div key={k.label} className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm text-center">
            <div className={`text-3xl font-bold ${k.color} mb-1`}>{k.value}</div>
            <div className="text-xs text-slate-400">{k.label}</div>
          </div>
        ))}
      </div>

      {/* Customer Table */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden mb-5">
        <div className="px-5 py-3.5 border-b border-slate-100 flex items-center justify-between">
          <span className="text-sm font-bold text-slate-900">Customer Organizations ({CUSTOMERS.length})</span>
        </div>
        <table className="w-full">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-100">
              {["Customer", "Industry", "Tier", "Readiness", "Workloads", "Threats", "Last Test", "Status", ""].map((h) => (
                <th key={h} className="text-[10px] font-bold uppercase tracking-wide text-slate-400 px-4 py-2.5 text-left">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {CUSTOMERS.map((c) => (
              <tr key={c.id} className="border-b border-slate-50 hover:bg-slate-50">
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${statusDot(c.status)}`} />
                    <span className="text-sm font-semibold text-slate-900">{c.name}</span>
                  </div>
                </td>
                <td className="px-4 py-3 text-sm text-slate-500">{c.industry}</td>
                <td className="px-4 py-3">
                  <span className={`text-[10px] font-bold uppercase border rounded px-2 py-0.5 ${tierBadge(c.tier)}`}>
                    {c.tier}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className={`text-xs font-bold px-2 py-0.5 rounded ${scoreColor(c.score)}`}>{c.score}</span>
                </td>
                <td className="px-4 py-3 text-sm text-slate-600">{c.workloads}</td>
                <td className="px-4 py-3">
                  <span className={`text-sm font-semibold ${c.threats > 0 ? "text-red-500" : "text-slate-400"}`}>
                    {c.threats}
                  </span>
                </td>
                <td className="px-4 py-3 text-sm text-slate-500">{c.lastTest}</td>
                <td className="px-4 py-3">
                  <span
                    className={`text-xs font-bold uppercase ${
                      c.status === "healthy"
                        ? "text-green-600"
                        : c.status === "warning"
                        ? "text-amber-500"
                        : "text-red-500"
                    }`}
                  >
                    {c.status}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <button className="text-xs text-slate-400 hover:text-green-600 font-semibold border border-slate-200 rounded px-2 py-1">
                    View
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Alert Rules */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        <div className="px-5 py-3.5 border-b border-slate-100 flex items-center justify-between">
          <span className="text-sm font-bold text-slate-900">Alert Rules (3)</span>
          <button className="text-xs text-slate-500 hover:text-green-600 font-semibold border border-slate-200 rounded px-3 py-1.5">
            Add Rule
          </button>
        </div>
        {[
          { on: true, name: "Critical score alert", condition: "readiness_below 50", scope: "All customers" },
          { on: true, name: "Active threat alert", condition: "threat_detected", scope: "tier:premium" },
          { on: false, name: "Stale test alert", condition: "no_test_in_days 14", scope: "All customers" },
        ].map((rule, i) => (
          <div key={i} className="flex items-center gap-4 px-5 py-3.5 border-b border-slate-50 last:border-0">
            <div
              className={`w-8 h-4 rounded-full flex-shrink-0 relative cursor-pointer ${rule.on ? "bg-green-500" : "bg-slate-300"}`}
            >
              <span
                className={`absolute top-0.5 w-3 h-3 bg-white rounded-full shadow transition-all ${rule.on ? "left-4" : "left-0.5"}`}
              />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-slate-900">{rule.name}</p>
              <p className="text-xs text-slate-400 mt-0.5">
                Condition: <code className="bg-slate-100 px-1 py-0.5 rounded text-[10px]">{rule.condition}</code>
                &nbsp; Applies to: {rule.scope}
              </p>
            </div>
            <span className="text-[10px] font-semibold bg-blue-50 text-blue-700 border border-blue-200 rounded px-2 py-0.5">
              email
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

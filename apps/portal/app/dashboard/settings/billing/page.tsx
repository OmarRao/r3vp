"use client";
import { useState } from "react";

const PLANS = [
  { id: "starter", name: "Starter", price: "$499", period: "/month", workloads: 10, features: ["10 workloads", "All providers", "SOC 2 / ISO 27001", "Email support"], current: false },
  { id: "growth", name: "Growth", price: "$1,499", period: "/month", workloads: 50, features: ["50 workloads", "All frameworks", "RBAC + SSO", "API keys", "Integrations", "Priority support"], current: true },
  { id: "enterprise", name: "Enterprise", price: "Custom", period: "", workloads: null, features: ["Unlimited workloads", "All features", "MSSP console", "Custom SLA", "Dedicated CSM"], current: false },
];

const MOCK_INVOICES = [
  { period: "Jun 2026", amount: "$1,499", status: "paid" },
  { period: "May 2026", amount: "$1,499", status: "paid" },
  { period: "Apr 2026", amount: "$1,499", status: "paid" },
];

export default function BillingPage() {
  return (
    <div className="p-7 bg-slate-50 min-h-screen">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-start justify-between mb-6">
          <div>
            <h1 className="text-xl font-bold text-slate-900">Billing and Usage</h1>
            <p className="text-sm text-slate-400 mt-1">Manage your subscription, usage, and invoices</p>
          </div>
          <button className="px-4 py-2 text-sm text-slate-600 border border-slate-200 rounded-md hover:bg-slate-50">Upgrade Plan</button>
        </div>

        <div className="bg-white border-l-4 border-l-green-500 border border-slate-200 rounded-xl p-5 mb-5 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-3">
              <span className="text-xs font-bold text-green-700 bg-green-50 border border-green-200 px-3 py-1 rounded uppercase">Growth</span>
              <span className="text-xs font-bold text-green-700 bg-green-50 border border-green-200 px-2 py-0.5 rounded">Active</span>
            </div>
            <div className="text-right">
              <span className="text-2xl font-bold text-slate-900">$1,499</span>
              <span className="text-sm text-slate-400">/month</span>
            </div>
          </div>
          <div className="flex items-center gap-2 mb-3">
            <div className="flex-1 bg-slate-100 rounded-full h-2">
              <div className="bg-amber-400 h-2 rounded-full" style={{width: "94%"}} />
            </div>
            <span className="text-xs text-slate-500 whitespace-nowrap">47 / 50 workloads</span>
          </div>
          <p className="text-xs text-slate-400">Renews Jul 1, 2026 · Next invoice: $1,499</p>
        </div>

        <div className="grid grid-cols-3 gap-4 mb-5">
          {PLANS.map(p => (
            <div key={p.id} className={`bg-white border rounded-xl p-5 shadow-sm ${p.current ? "border-green-400" : "border-slate-200"}`}>
              {p.current && <div className="text-[10px] font-bold text-green-700 bg-green-50 border border-green-200 px-2 py-0.5 rounded mb-2 w-fit">Current Plan</div>}
              <h3 className="font-bold text-slate-900 mb-1">{p.name}</h3>
              <div className="text-xl font-bold text-slate-900 mb-3">{p.price}<span className="text-xs font-normal text-slate-400">{p.period}</span></div>
              <ul className="space-y-1 mb-4">
                {p.features.map(f => <li key={f} className="text-xs text-slate-500 flex items-center gap-1"><span className="text-green-500">✓</span>{f}</li>)}
              </ul>
              {!p.current && <button className={`w-full py-1.5 text-xs font-semibold rounded ${p.id === "enterprise" ? "bg-green-500 text-white" : "border border-slate-200 text-slate-600 hover:bg-slate-50"}`}>{p.id === "enterprise" ? "Contact Sales" : "Downgrade"}</button>}
            </div>
          ))}
        </div>

        <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
          <div className="px-5 py-3.5 border-b border-slate-100"><span className="text-sm font-bold text-slate-900">Invoices</span></div>
          <table className="w-full">
            <thead><tr className="bg-slate-50 border-b border-slate-100">
              {["Period", "Amount", "Status", "Actions"].map(h => <th key={h} className="text-[10px] font-bold uppercase tracking-wide text-slate-400 px-5 py-2.5 text-left">{h}</th>)}
            </tr></thead>
            <tbody>
              {MOCK_INVOICES.map(inv => (
                <tr key={inv.period} className="border-b border-slate-50 hover:bg-slate-50">
                  <td className="px-5 py-3 text-sm text-slate-700">{inv.period}</td>
                  <td className="px-5 py-3 text-sm font-semibold text-slate-900">{inv.amount}</td>
                  <td className="px-5 py-3"><span className="text-xs font-bold text-green-700 bg-green-50 border border-green-200 px-2 py-0.5 rounded uppercase">{inv.status}</span></td>
                  <td className="px-5 py-3"><button className="text-xs text-slate-400 hover:text-green-600 font-semibold">Download</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

"use client";
import { useState } from "react";

const EXAMPLE_QUERIES = [
  "Which workloads are at risk?",
  "How many RTO breaches this quarter?",
  "What is our worst performing provider?",
  "Which workloads have not been tested recently?",
];

const MOCK_RISKS = [
  { rank: 1, workload: "sql-prod-02", provider: "aws", score: 70, level: "high", reasons: ["RTO at 106% of target", "Fail rate 50%"] },
  { rank: 2, workload: "db-prod-03", provider: "vmware", score: 55, level: "high", reasons: ["RTO at 87% of target", "Fail rate 33%"] },
  { rank: 3, workload: "auth-svc-01", provider: "azure", score: 45, level: "medium", reasons: ["Not tested in 45 days"] },
  { rank: 4, workload: "erp-prod-01", provider: "vmware", score: 38, level: "medium", reasons: ["Fail rate 33%"] },
  { rank: 5, workload: "dc-01.prod", provider: "hyperv", score: 5, level: "low", reasons: [] },
];

const LEVEL_COLORS: Record<string, string> = {
  high: "bg-red-50 text-red-700 border-red-200",
  medium: "bg-amber-50 text-amber-700 border-amber-200",
  low: "bg-green-50 text-green-700 border-green-200",
};

export default function InsightsPage() {
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleQuery = async (q: string) => {
    setQuery(q);
    setLoading(true);
    setAnswer(null);
    await new Promise(r => setTimeout(r, 600));
    const answers: Record<string, string> = {
      "Which workloads are at risk?": "2 workloads are at HIGH risk: sql-prod-02 (RTO breach, 50% fail rate) and db-prod-03 (degrading trend). 2 more are at MEDIUM risk.",
      "How many RTO breaches this quarter?": "1 workload breached its RTO target this quarter: sql-prod-02 at 95 minutes against a 90 minute target.",
      "What is our worst performing provider?": "AWS has the lowest pass rate at 75%, driven by sql-prod-02 failures. Hyper-V has the highest at 100%.",
      "Which workloads have not been tested recently?": "1 workload has not been tested in over 30 days: auth-svc-01 (45 days since last test).",
    };
    setAnswer(answers[q] || "I can answer questions about workload counts, test failures, RTO breaches, threats, and provider performance.");
    setLoading(false);
  };

  return (
    <div className="p-7 bg-slate-50 min-h-screen">
      <div className="max-w-5xl mx-auto">
        <div className="mb-6">
          <h1 className="text-xl font-bold text-slate-900">AI Insights</h1>
          <p className="text-sm text-slate-400 mt-1">Predictive analytics, anomaly detection, and natural language queries</p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-6 mb-5 shadow-sm">
          <div className="flex gap-3 mb-3">
            <input
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => e.key === "Enter" && query && handleQuery(query)}
              placeholder="Ask a question about your recovery posture..."
              className="flex-1 border border-slate-200 rounded-md px-4 py-2.5 text-sm outline-none focus:border-green-400"
            />
            <button onClick={() => query && handleQuery(query)} disabled={loading} className="px-4 py-2 bg-green-500 hover:bg-green-600 text-white text-sm font-semibold rounded-md disabled:opacity-50">
              {loading ? "..." : "Ask"}
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            {EXAMPLE_QUERIES.map(q => (
              <button key={q} onClick={() => handleQuery(q)} className="text-xs text-slate-500 border border-slate-200 rounded-full px-3 py-1 hover:border-green-400 hover:text-green-700">
                {q}
              </button>
            ))}
          </div>
          {answer && (
            <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg text-sm text-slate-800">
              <span className="font-semibold text-green-700 block mb-1">Answer</span>
              {answer}
            </div>
          )}
        </div>

        <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden mb-5">
          <div className="px-5 py-3.5 border-b border-slate-100">
            <span className="text-sm font-bold text-slate-900">Workload Risk Ranking</span>
            <span className="text-xs text-slate-400 ml-2">Scored by test recency, RTO ratio, and failure rate</span>
          </div>
          <table className="w-full">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-100">
                {["Rank", "Workload", "Provider", "Risk Score", "Risk Level", "Reasons"].map(h => (
                  <th key={h} className="text-[10px] font-bold uppercase tracking-wide text-slate-400 px-5 py-2.5 text-left">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {MOCK_RISKS.map(r => (
                <tr key={r.rank} className="border-b border-slate-50 hover:bg-slate-50">
                  <td className="px-5 py-3 text-sm text-slate-400">#{r.rank}</td>
                  <td className="px-5 py-3 text-sm font-semibold text-slate-900">{r.workload}</td>
                  <td className="px-5 py-3 text-sm text-slate-500 capitalize">{r.provider}</td>
                  <td className="px-5 py-3 text-sm font-bold text-slate-700">{r.score}</td>
                  <td className="px-5 py-3">
                    <span className={`text-xs font-bold border px-2 py-0.5 rounded uppercase ${LEVEL_COLORS[r.level]}`}>{r.level}</span>
                  </td>
                  <td className="px-5 py-3 text-xs text-slate-500">{r.reasons.join(" · ") || "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

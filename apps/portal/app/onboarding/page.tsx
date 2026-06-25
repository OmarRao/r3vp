"use client";
import { useState } from "react";

const STEPS = [
  { step: 1, id: "org_profile", title: "Organization Profile", desc: "Configure your org and recovery objectives" },
  { step: 2, id: "deploy_appliance", title: "Deploy Appliance", desc: "Deploy the R3VP appliance in your environment" },
  { step: 3, id: "connect_veeam", title: "Connect Veeam", desc: "Connect to your Veeam B&R server" },
  { step: 4, id: "discover_workloads", title: "Discover Workloads", desc: "Sync your protected VM inventory" },
  { step: 5, id: "first_test", title: "Run First Test", desc: "Validate your first workload recovery" },
  { step: 6, id: "complete", title: "Done", desc: "Setup complete" },
];

export default function OnboardingPage() {
  const [currentStep, setCurrentStep] = useState(1);
  const [form, setForm] = useState({ org_name: "", industry: "Financial Services", rto: "60", rpo: "24" });

  const progress = Math.round(((currentStep - 1) / (STEPS.length - 1)) * 100);

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
      <div className="w-full max-w-2xl">
        <div className="text-center mb-8">
          <span className="text-2xl font-bold text-slate-900">R3VP</span>
          <span className="text-sm text-green-500 font-semibold ml-2">Setup</span>
        </div>

        <div className="flex items-center justify-between mb-8">
          {STEPS.map((s, i) => (
            <div key={s.step} className="flex items-center flex-1">
              <div className="flex flex-col items-center">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold border-2 transition-colors ${s.step < currentStep ? "bg-green-500 border-green-500 text-white" : s.step === currentStep ? "bg-green-500 border-green-500 text-white" : "bg-white border-slate-300 text-slate-400"}`}>
                  {s.step < currentStep ? "✓" : s.step}
                </div>
                <span className="text-[10px] text-slate-400 mt-1 w-16 text-center leading-tight">{s.title}</span>
              </div>
              {i < STEPS.length - 1 && <div className={`flex-1 h-0.5 mx-1 mb-5 ${s.step < currentStep ? "bg-green-500" : "bg-slate-200"}`} />}
            </div>
          ))}
        </div>

        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-8 mb-4">
          {currentStep === 1 && (
            <>
              <h2 className="text-xl font-bold text-slate-900 mb-1">Organization Profile</h2>
              <p className="text-sm text-slate-400 mb-6">Configure your organization and default recovery objectives</p>
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div className="col-span-2">
                  <label className="text-xs font-semibold text-slate-600 block mb-1">Organization Name</label>
                  <input value={form.org_name} onChange={e => setForm({...form, org_name: e.target.value})} placeholder="Acme Corporation" className="w-full border border-slate-200 rounded-md px-3 py-2 text-sm outline-none focus:border-green-400" />
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-600 block mb-1">Industry</label>
                  <select value={form.industry} onChange={e => setForm({...form, industry: e.target.value})} className="w-full border border-slate-200 rounded-md px-3 py-2 text-sm outline-none focus:border-green-400 bg-white">
                    {["Financial Services", "Healthcare", "Technology", "Manufacturing", "Retail", "Government", "Other"].map(i => <option key={i}>{i}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs font-semibold text-slate-600 block mb-1">Default RTO Target (minutes)</label>
                  <input type="number" value={form.rto} onChange={e => setForm({...form, rto: e.target.value})} className="w-full border border-slate-200 rounded-md px-3 py-2 text-sm outline-none focus:border-green-400" />
                </div>
              </div>
              <div className="p-4 bg-blue-50 border border-blue-100 rounded-lg text-xs text-blue-700 mb-4">
                Credentials are encrypted with SOPS and age and never leave your environment. R3VP only stores test results and metadata in the cloud.
              </div>
            </>
          )}
          {currentStep === 2 && (
            <>
              <h2 className="text-xl font-bold text-slate-900 mb-1">Deploy Appliance</h2>
              <p className="text-sm text-slate-400 mb-6">Run the R3VP appliance inside your environment</p>
              <div className="mb-4">
                <p className="text-xs font-semibold text-slate-600 mb-2">Docker (recommended)</p>
                <div className="bg-slate-900 rounded-lg p-4 font-mono text-xs text-green-400">
                  docker run -d --name r3vp-appliance \<br/>
                  {"  "}-e R3VP_TOKEN=rgt_xxxxxxxxxxxxx \<br/>
                  {"  "}-e R3VP_API_URL=https://api.r3vp.io \<br/>
                  {"  "}r3vp/appliance:latest
                </div>
              </div>
              <div className="flex items-center gap-3 p-4 bg-green-50 border border-green-200 rounded-lg text-sm">
                <span className="text-green-500 text-lg">⏳</span>
                <span className="text-slate-600">Waiting for appliance to connect...</span>
              </div>
            </>
          )}
          {currentStep > 2 && (
            <div className="text-center py-8">
              <div className="text-4xl mb-3">{currentStep === 6 ? "🎉" : "✅"}</div>
              <h2 className="text-xl font-bold text-slate-900 mb-2">{STEPS[currentStep - 1]?.title}</h2>
              <p className="text-sm text-slate-400">{STEPS[currentStep - 1]?.desc}</p>
            </div>
          )}
          <div className="flex justify-between mt-6">
            <button onClick={() => setCurrentStep(Math.max(1, currentStep - 1))} disabled={currentStep === 1} className="px-4 py-2 text-sm text-slate-500 border border-slate-200 rounded-md hover:bg-slate-50 disabled:opacity-30">Back</button>
            <button onClick={() => setCurrentStep(Math.min(6, currentStep + 1))} className="px-4 py-2 bg-green-500 hover:bg-green-600 text-white text-sm font-semibold rounded-md">
              {currentStep === 6 ? "Go to Dashboard" : "Continue"}
            </button>
          </div>
        </div>

        <p className="text-center text-xs text-slate-400">Step {currentStep} of {STEPS.length}</p>
      </div>
    </div>
  );
}

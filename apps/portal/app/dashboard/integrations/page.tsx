"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

interface NotificationChannel {
  id: string;
  name: string;
  channel_type: string;
  destination: string;
  events: string[];
  enabled: boolean;
}

export default function IntegrationsPage() {
  const qc = useQueryClient();

  const { data: channels = [] } = useQuery<NotificationChannel[]>({
    queryKey: ["notification-channels"],
    queryFn: () => api.get("/v1/notifications").then((r) => r.data),
  });

  const [soarForm, setSoarForm] = useState({ platform: "splunk_soar", url: "", api_key: "" });
  const [siemForm, setSiemForm] = useState({
    platform: "sentinel",
    host: "",
    port: "514",
    format: "cef",
  });
  const [veeamoneForm, setVeeamoneForm] = useState({ url: "", username: "", password: "" });
  const [saved, setSaved] = useState<Record<string, boolean>>({});

  const addChannelMutation = useMutation({
    mutationFn: (data: object) => api.post("/v1/notifications", data).then((r) => r.data),
    onSuccess: (_res, vars: any) => {
      qc.invalidateQueries({ queryKey: ["notification-channels"] });
      setSaved((s) => ({ ...s, [vars._key]: true }));
      setTimeout(() => setSaved((s) => ({ ...s, [vars._key]: false })), 3000);
    },
  });

  const deleteChannelMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/v1/notifications/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notification-channels"] }),
  });

  function saveSoar() {
    addChannelMutation.mutate({
      _key: "soar",
      name: soarForm.platform,
      channel_type: "soar",
      destination: soarForm.url,
      events: ["threat_detected"],
      enabled: true,
    });
  }

  function saveSiem() {
    addChannelMutation.mutate({
      _key: "siem",
      name: `${siemForm.platform} SIEM`,
      channel_type: "siem",
      destination: `${siemForm.host}:${siemForm.port}`,
      events: ["threat_detected", "test_failed"],
      enabled: true,
    });
  }

  function saveVeeamone() {
    addChannelMutation.mutate({
      _key: "veeamone",
      name: "VeeamONE",
      channel_type: "veeamone",
      destination: `${veeamoneForm.url}|${veeamoneForm.username}|${veeamoneForm.password}`,
      events: ["threat_detected", "test_failed", "rto_breach", "rpo_breach"],
      enabled: true,
    });
  }

  const soarChannels = channels.filter((c) => c.channel_type === "soar");
  const siemChannels = channels.filter((c) => c.channel_type === "siem");
  const veeamoneChannels = channels.filter((c) => c.channel_type === "veeamone");

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Integrations</h1>
        <p className="text-sm text-gray-500 mt-1">
          Configure SOAR, SIEM, and VeeamONE integrations for automated incident response.
        </p>
      </div>

      {/* SOAR */}
      <div className="bg-white rounded-xl shadow p-5">
        <h2 className="text-lg font-semibold mb-1">SOAR Integration</h2>
        <p className="text-xs text-gray-400 mb-4">
          Dispatch threat detection events to your SOAR platform automatically on critical and high
          severity findings.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div>
            <label className="block text-xs text-gray-600 mb-1">Platform</label>
            <select
              value={soarForm.platform}
              onChange={(e) => setSoarForm((f) => ({ ...f, platform: e.target.value }))}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-veeam-green"
            >
              <option value="splunk_soar">Splunk SOAR (Phantom)</option>
              <option value="xsoar">Palo Alto XSOAR</option>
              <option value="generic">Generic Webhook</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-600 mb-1">Webhook URL</label>
            <input
              type="url"
              value={soarForm.url}
              onChange={(e) => setSoarForm((f) => ({ ...f, url: e.target.value }))}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-veeam-green"
              placeholder="https://soar.example.com"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-600 mb-1">API Key / Token</label>
            <input
              type="password"
              value={soarForm.api_key}
              onChange={(e) => setSoarForm((f) => ({ ...f, api_key: e.target.value }))}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-veeam-green"
              placeholder="api-token"
            />
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={saveSoar}
            disabled={addChannelMutation.isPending}
            className="bg-veeam-green text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-60 transition-colors"
          >
            Save SOAR Config
          </button>
          {saved.soar && <span className="text-sm text-green-600 font-medium">Saved!</span>}
        </div>
        {soarChannels.length > 0 && (
          <div className="mt-4 space-y-2">
            {soarChannels.map((c) => (
              <div
                key={c.id}
                className="flex items-center justify-between text-sm bg-gray-50 rounded-lg px-3 py-2"
              >
                <span className="font-medium">{c.name}</span>
                <span className="text-gray-400 text-xs">{c.destination}</span>
                <button
                  onClick={() => deleteChannelMutation.mutate(c.id)}
                  className="text-red-500 text-xs hover:text-red-700"
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* SIEM */}
      <div className="bg-white rounded-xl shadow p-5">
        <h2 className="text-lg font-semibold mb-1">SIEM Integration</h2>
        <p className="text-xs text-gray-400 mb-4">
          Emit CEF, LEEF, or JSON syslog events to Splunk, IBM QRadar, or Microsoft Sentinel.
        </p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
          <div>
            <label className="block text-xs text-gray-600 mb-1">Platform</label>
            <select
              value={siemForm.platform}
              onChange={(e) => setSiemForm((f) => ({ ...f, platform: e.target.value }))}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-veeam-green"
            >
              <option value="sentinel">Microsoft Sentinel</option>
              <option value="splunk">Splunk</option>
              <option value="qradar">IBM QRadar</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-600 mb-1">Syslog Host</label>
            <input
              type="text"
              value={siemForm.host}
              onChange={(e) => setSiemForm((f) => ({ ...f, host: e.target.value }))}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-veeam-green"
              placeholder="siem.example.com"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-600 mb-1">Port</label>
            <input
              type="number"
              value={siemForm.port}
              onChange={(e) => setSiemForm((f) => ({ ...f, port: e.target.value }))}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-veeam-green"
              placeholder="514"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-600 mb-1">Format</label>
            <select
              value={siemForm.format}
              onChange={(e) => setSiemForm((f) => ({ ...f, format: e.target.value }))}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-veeam-green"
            >
              <option value="cef">CEF (Splunk, ArcSight)</option>
              <option value="leef">LEEF (QRadar)</option>
              <option value="json">JSON Syslog (Sentinel)</option>
            </select>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={saveSiem}
            disabled={addChannelMutation.isPending}
            className="bg-veeam-green text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-60 transition-colors"
          >
            Save SIEM Config
          </button>
          {saved.siem && <span className="text-sm text-green-600 font-medium">Saved!</span>}
        </div>
        {siemChannels.length > 0 && (
          <div className="mt-4 space-y-2">
            {siemChannels.map((c) => (
              <div
                key={c.id}
                className="flex items-center justify-between text-sm bg-gray-50 rounded-lg px-3 py-2"
              >
                <span className="font-medium">{c.name}</span>
                <span className="text-gray-400 text-xs">{c.destination}</span>
                <button
                  onClick={() => deleteChannelMutation.mutate(c.id)}
                  className="text-red-500 text-xs hover:text-red-700"
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* VeeamONE */}
      <div className="bg-white rounded-xl shadow p-5">
        <h2 className="text-lg font-semibold mb-1">VeeamONE Integration</h2>
        <p className="text-xs text-gray-400 mb-4">
          Push recovery test results and threat events to VeeamONE as custom alarms.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div>
            <label className="block text-xs text-gray-600 mb-1">VeeamONE URL</label>
            <input
              type="url"
              value={veeamoneForm.url}
              onChange={(e) => setVeeamoneForm((f) => ({ ...f, url: e.target.value }))}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-veeam-green"
              placeholder="https://veeamone.example.com"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-600 mb-1">Username</label>
            <input
              type="text"
              value={veeamoneForm.username}
              onChange={(e) => setVeeamoneForm((f) => ({ ...f, username: e.target.value }))}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-veeam-green"
              placeholder="administrator"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-600 mb-1">Password</label>
            <input
              type="password"
              value={veeamoneForm.password}
              onChange={(e) => setVeeamoneForm((f) => ({ ...f, password: e.target.value }))}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-veeam-green"
              placeholder="password"
            />
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={saveVeeamone}
            disabled={addChannelMutation.isPending}
            className="bg-veeam-green text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-60 transition-colors"
          >
            Save VeeamONE Config
          </button>
          {saved.veeamone && <span className="text-sm text-green-600 font-medium">Saved!</span>}
        </div>
        {veeamoneChannels.length > 0 && (
          <div className="mt-4 space-y-2">
            {veeamoneChannels.map((c) => (
              <div
                key={c.id}
                className="flex items-center justify-between text-sm bg-gray-50 rounded-lg px-3 py-2"
              >
                <span className="font-medium">{c.name}</span>
                <span className="text-gray-400 text-xs">{c.destination.split("|")[0]}</span>
                <button
                  onClick={() => deleteChannelMutation.mutate(c.id)}
                  className="text-red-500 text-xs hover:text-red-700"
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <p className="text-xs text-gray-400 text-center pt-2">
        Built by{" "}
        <a
          href="https://www.linkedin.com/in/omarrao/"
          target="_blank"
          rel="noopener noreferrer"
          className="text-veeam-green hover:underline"
        >
          Omar Rao
        </a>
        , Engineer - Data Resilience, Cybersecurity and Privacy
      </p>
    </div>
  );
}

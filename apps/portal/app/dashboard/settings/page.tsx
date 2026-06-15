"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import { api } from "@/lib/api";

interface Org {
  id: string;
  name: string;
}

interface OrgDefaults {
  default_rto_mins: number | null;
  default_rpo_mins: number | null;
}

interface NotificationChannel {
  id: string;
  name: string;
  type: "email" | "slack" | "teams";
  destination: string;
  events: string[];
}

const typeBadge: Record<string, string> = {
  email: "bg-blue-100 text-blue-800",
  slack: "bg-purple-100 text-purple-800",
  teams: "bg-indigo-100 text-indigo-800",
};

const EVENT_OPTIONS = [
  { label: "Test Failed", value: "test_failed" },
  { label: "RTO Breach", value: "rto_breach" },
  { label: "RPO Breach", value: "rpo_breach" },
];

const destinationPlaceholder = (type: string) => {
  if (type === "email") return "Email address";
  if (type === "slack") return "Slack webhook URL";
  return "Teams webhook URL";
};

function useFeedback() {
  const [success, setSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const showSuccess = (msg: string) => {
    setSuccess(msg);
    setError(null);
    setTimeout(() => setSuccess(null), 3000);
  };
  const showError = (msg: string) => {
    setError(msg);
    setSuccess(null);
  };

  return { success, error, showSuccess, showError };
}

export default function SettingsPage() {
  const qc = useQueryClient();

  // Section 1: Org
  const { data: org, isLoading: orgLoading } = useQuery<Org>({
    queryKey: ["org"],
    queryFn: () => api.get("/v1/org").then((r) => r.data),
    retry: false,
  });

  const [orgName, setOrgName] = useState("");
  useEffect(() => {
    if (org?.name) setOrgName(org.name);
  }, [org]);

  const orgFeedback = useFeedback();
  const saveOrgMutation = useMutation({
    mutationFn: () => api.put("/v1/org", { name: orgName }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["org"] });
      orgFeedback.showSuccess("Saved!");
    },
    onError: () => orgFeedback.showError("Failed to save organization name."),
  });

  // Section 2: Notification Channels
  const { data: channels = [], isLoading: channelsLoading } = useQuery<NotificationChannel[]>({
    queryKey: ["notifications"],
    queryFn: () => api.get("/v1/notifications").then((r) => r.data),
    retry: false,
  });

  const [newName, setNewName] = useState("");
  const [newType, setNewType] = useState<"email" | "slack" | "teams">("email");
  const [newDest, setNewDest] = useState("");
  const [newEvents, setNewEvents] = useState<string[]>(["test_failed", "rto_breach", "rpo_breach"]);

  const channelFeedback = useFeedback();

  const addChannelMutation = useMutation({
    mutationFn: () =>
      api.post("/v1/notifications", {
        name: newName,
        type: newType,
        destination: newDest,
        events: newEvents,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["notifications"] });
      setNewName("");
      setNewDest("");
      setNewEvents(["test_failed", "rto_breach", "rpo_breach"]);
      channelFeedback.showSuccess("Channel added.");
    },
    onError: () => channelFeedback.showError("Failed to add channel."),
  });

  const deleteChannelMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/v1/notifications/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  const toggleEvent = (value: string) => {
    setNewEvents((prev) =>
      prev.includes(value) ? prev.filter((e) => e !== value) : [...prev, value]
    );
  };

  // Section 3: Default Targets
  const { data: defaults, isLoading: defaultsLoading } = useQuery<OrgDefaults>({
    queryKey: ["org-defaults"],
    queryFn: () => api.get("/v1/org/defaults").then((r) => r.data),
    retry: false,
  });

  const [defaultRto, setDefaultRto] = useState("");
  const [defaultRpo, setDefaultRpo] = useState("");
  useEffect(() => {
    if (defaults?.default_rto_mins != null) setDefaultRto(String(defaults.default_rto_mins));
    if (defaults?.default_rpo_mins != null) setDefaultRpo(String(defaults.default_rpo_mins));
  }, [defaults]);

  const defaultsFeedback = useFeedback();
  const saveDefaultsMutation = useMutation({
    mutationFn: () =>
      api.put("/v1/org/defaults", {
        default_rto_mins: defaultRto ? Number(defaultRto) : null,
        default_rpo_mins: defaultRpo ? Number(defaultRpo) : null,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["org-defaults"] });
      defaultsFeedback.showSuccess("Saved!");
    },
    onError: () => defaultsFeedback.showError("Failed to save defaults."),
  });

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Settings</h1>

      {/* Section 1: Organization */}
      <div className="bg-white rounded-xl shadow p-5 space-y-4">
        <h2 className="text-lg font-semibold text-gray-900">Organization</h2>
        {orgLoading ? (
          <div className="flex items-center gap-2">
            <div className="animate-spin border-4 rounded-full w-5 h-5 border-green-500 border-t-transparent" />
            <span className="text-sm text-gray-400">Loading...</span>
          </div>
        ) : !org ? (
          <p className="text-sm text-gray-400 italic">
            Organization details unavailable. The endpoint may not be configured yet.
          </p>
        ) : (
          <div className="space-y-4">
            <div>
              <label className="block text-sm text-gray-600 mb-1">Org ID</label>
              <p className="font-mono text-sm text-gray-800 bg-gray-50 border border-gray-200 rounded px-3 py-2">
                {org.id}
              </p>
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">Org Name</label>
              <div className="flex items-center gap-3">
                <input
                  type="text"
                  value={orgName}
                  onChange={(e) => setOrgName(e.target.value)}
                  className="border border-gray-300 rounded-lg px-3 py-2 text-sm w-72 focus:outline-none focus:ring-2 focus:ring-veeam-green"
                />
                <button
                  onClick={() => saveOrgMutation.mutate()}
                  disabled={saveOrgMutation.isPending}
                  className="bg-veeam-green text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-60 transition-colors"
                >
                  {saveOrgMutation.isPending ? "Saving..." : "Save"}
                </button>
                {orgFeedback.success && (
                  <span className="text-sm text-green-600 font-medium">{orgFeedback.success}</span>
                )}
                {orgFeedback.error && (
                  <span className="text-sm text-red-600">{orgFeedback.error}</span>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Section 2: Notification Channels */}
      <div className="bg-white rounded-xl shadow p-5 space-y-4">
        <h2 className="text-lg font-semibold text-gray-900">Notification Channels</h2>
        {channelsLoading ? (
          <div className="flex items-center gap-2">
            <div className="animate-spin border-4 rounded-full w-5 h-5 border-green-500 border-t-transparent" />
            <span className="text-sm text-gray-400">Loading...</span>
          </div>
        ) : channels.length === 0 ? (
          <p className="text-sm text-gray-400">No notification channels configured yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b text-left text-gray-500 text-xs uppercase tracking-wide">
                  <th className="pb-2 pr-4">Name</th>
                  <th className="pb-2 pr-4">Type</th>
                  <th className="pb-2 pr-4">Destination</th>
                  <th className="pb-2 pr-4">Events</th>
                  <th className="pb-2">Actions</th>
                </tr>
              </thead>
              <tbody>
                {channels.map((ch) => (
                  <tr key={ch.id} className="border-b hover:bg-gray-50">
                    <td className="py-2 pr-4 font-medium text-gray-900">{ch.name}</td>
                    <td className="py-2 pr-4">
                      <span
                        className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                          typeBadge[ch.type] ?? "bg-gray-100 text-gray-600"
                        }`}
                      >
                        {ch.type}
                      </span>
                    </td>
                    <td className="py-2 pr-4 text-gray-600 text-xs truncate max-w-xs">
                      {ch.destination}
                    </td>
                    <td className="py-2 pr-4 text-gray-500 text-xs">
                      {ch.events.join(", ")}
                    </td>
                    <td className="py-2">
                      <button
                        onClick={() => deleteChannelMutation.mutate(ch.id)}
                        disabled={deleteChannelMutation.isPending}
                        className="text-red-600 hover:text-red-800 text-xs font-medium disabled:opacity-50"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Add Channel form */}
        <div className="border-t pt-4 space-y-3">
          <h3 className="text-sm font-semibold text-gray-700">Add Channel</h3>
          <div className="flex flex-wrap gap-3 items-end">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Name</label>
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="e.g. Ops Team"
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm w-40 focus:outline-none focus:ring-2 focus:ring-veeam-green"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Type</label>
              <select
                value={newType}
                onChange={(e) => setNewType(e.target.value as "email" | "slack" | "teams")}
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-veeam-green"
              >
                <option value="email">email</option>
                <option value="slack">slack</option>
                <option value="teams">teams</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Destination</label>
              <input
                type="text"
                value={newDest}
                onChange={(e) => setNewDest(e.target.value)}
                placeholder={destinationPlaceholder(newType)}
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm w-64 focus:outline-none focus:ring-2 focus:ring-veeam-green"
              />
            </div>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Events</label>
            <div className="flex flex-wrap gap-4">
              {EVENT_OPTIONS.map((opt) => (
                <label key={opt.value} className="flex items-center gap-1.5 text-sm text-gray-700 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={newEvents.includes(opt.value)}
                    onChange={() => toggleEvent(opt.value)}
                    className="accent-veeam-green"
                  />
                  {opt.label}
                </label>
              ))}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => addChannelMutation.mutate()}
              disabled={addChannelMutation.isPending || !newName || !newDest}
              className="bg-veeam-green text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-60 transition-colors"
            >
              {addChannelMutation.isPending ? "Adding..." : "Add Channel"}
            </button>
            {channelFeedback.success && (
              <span className="text-sm text-green-600 font-medium">{channelFeedback.success}</span>
            )}
            {channelFeedback.error && (
              <span className="text-sm text-red-600">{channelFeedback.error}</span>
            )}
          </div>
        </div>
      </div>

      {/* Section 3: Default Targets */}
      <div className="bg-white rounded-xl shadow p-5 space-y-4">
        <h2 className="text-lg font-semibold text-gray-900">Default Targets</h2>
        <p className="text-sm text-gray-500">
          These values pre-fill when adding new workloads.
        </p>
        {defaultsLoading ? (
          <div className="flex items-center gap-2">
            <div className="animate-spin border-4 rounded-full w-5 h-5 border-green-500 border-t-transparent" />
            <span className="text-sm text-gray-400">Loading...</span>
          </div>
        ) : (
          <div className="flex flex-wrap gap-4 items-end">
            <div>
              <label className="block text-sm text-gray-600 mb-1">Default RTO (mins)</label>
              <input
                type="number"
                min={0}
                value={defaultRto}
                onChange={(e) => setDefaultRto(e.target.value)}
                placeholder="e.g. 60"
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm w-36 focus:outline-none focus:ring-2 focus:ring-veeam-green"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-600 mb-1">Default RPO (mins)</label>
              <input
                type="number"
                min={0}
                value={defaultRpo}
                onChange={(e) => setDefaultRpo(e.target.value)}
                placeholder="e.g. 15"
                className="border border-gray-300 rounded-lg px-3 py-2 text-sm w-36 focus:outline-none focus:ring-2 focus:ring-veeam-green"
              />
            </div>
            <button
              onClick={() => saveDefaultsMutation.mutate()}
              disabled={saveDefaultsMutation.isPending}
              className="bg-veeam-green text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-60 transition-colors"
            >
              {saveDefaultsMutation.isPending ? "Saving..." : "Save"}
            </button>
            {defaultsFeedback.success && (
              <span className="text-sm text-green-600 font-medium">{defaultsFeedback.success}</span>
            )}
            {defaultsFeedback.error && (
              <span className="text-sm text-red-600">{defaultsFeedback.error}</span>
            )}
          </div>
        )}
      </div>

      {/* Footer */}
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

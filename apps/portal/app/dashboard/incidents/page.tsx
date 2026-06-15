"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

interface IrLogEntry {
  step: string;
  detail: string;
  success: boolean;
  ts: string;
}

interface Incident {
  id: string;
  incident_number: string;
  title: string;
  severity: string;
  status: string;
  affected_host: string;
  threat_name: string;
  backup_triggered: boolean;
  backup_job_id: string | null;
  soar_dispatched: boolean;
  soar_incident_id: string | null;
  siem_dispatched: boolean;
  veeamone_reported: boolean;
  notifications_sent: boolean;
  ir_log: IrLogEntry[];
  created_at: string;
  resolved_at: string | null;
}

const severityBadge: Record<string, string> = {
  critical: "bg-red-100 text-red-800",
  high: "bg-orange-100 text-orange-800",
  medium: "bg-yellow-100 text-yellow-800",
  low: "bg-green-100 text-green-800",
};

const statusBadge: Record<string, string> = {
  active: "bg-red-100 text-red-700",
  contained: "bg-yellow-100 text-yellow-700",
  resolved: "bg-green-100 text-green-700",
};

function IntegrationStatus({ ok, label }: { ok: boolean; label: string }) {
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-gray-50 last:border-0">
      <span className="text-xs text-gray-500">{label}</span>
      <span className={`text-xs font-semibold ${ok ? "text-green-600" : "text-gray-400"}`}>
        {ok ? "Dispatched" : "Not sent"}
      </span>
    </div>
  );
}

export default function IncidentsPage() {
  const qc = useQueryClient();

  const { data: incidents = [], isLoading } = useQuery<Incident[]>({
    queryKey: ["incidents"],
    queryFn: () => api.get("/v1/threat-intel/incidents").then((r) => r.data),
    refetchInterval: 10000,
  });

  const resolveMutation = useMutation({
    mutationFn: (id: string) =>
      api.patch(`/v1/threat-intel/incidents/${id}/resolve`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["incidents"] }),
  });

  const activeIncidents = incidents.filter((i) => i.status !== "resolved");
  const resolvedIncidents = incidents.filter((i) => i.status === "resolved");

  function renderIncident(incident: Incident) {
    return (
      <div
        key={incident.id}
        className={`bg-white rounded-xl shadow p-5 border-l-4 ${
          incident.status === "active" ? "border-red-500" : "border-green-400"
        }`}
      >
        <div className="flex items-start justify-between gap-4 mb-4">
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="text-base font-bold text-gray-900">{incident.incident_number}</h2>
              <span
                className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                  severityBadge[incident.severity] ?? ""
                }`}
              >
                {incident.severity}
              </span>
              <span
                className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                  statusBadge[incident.status] ?? ""
                }`}
              >
                {incident.status}
              </span>
            </div>
            <p className="text-sm text-gray-700 mt-1">{incident.title}</p>
            <p className="text-xs text-gray-400 mt-1">
              {incident.affected_host} &bull; Started{" "}
              {new Date(incident.created_at).toLocaleString()}
            </p>
          </div>
          {incident.status === "active" && (
            <button
              onClick={() => resolveMutation.mutate(incident.id)}
              disabled={resolveMutation.isPending}
              className="shrink-0 bg-green-600 text-white text-xs px-3 py-1.5 rounded-lg font-medium hover:bg-green-700 disabled:opacity-60 transition-colors"
            >
              Mark Resolved
            </button>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
              Incident Response Workflow
            </h3>
            <div className="space-y-0">
              {incident.ir_log.map((entry, idx) => (
                <div key={idx} className="flex gap-3 py-2 border-b border-gray-50 last:border-0">
                  <div
                    className={`w-5 h-5 rounded-full flex items-center justify-center text-xs shrink-0 mt-0.5 ${
                      entry.success
                        ? "bg-green-100 text-green-600"
                        : "bg-red-100 text-red-600"
                    }`}
                  >
                    {entry.success ? "✓" : "✗"}
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-gray-700 capitalize">
                      {entry.step.replace(/_/g, " ")}
                    </p>
                    <p className="text-xs text-gray-500">{entry.detail}</p>
                    <p className="text-xs text-gray-300 mt-0.5">
                      {new Date(entry.ts).toLocaleTimeString()}
                    </p>
                  </div>
                </div>
              ))}
              {incident.ir_log.length === 0 && (
                <p className="text-xs text-gray-400">No IR log entries yet.</p>
              )}
            </div>
          </div>

          <div>
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
              Integration Status
            </h3>
            <IntegrationStatus ok={incident.backup_triggered} label="Pre-incident Backup" />
            <IntegrationStatus ok={incident.soar_dispatched} label="SOAR Alert" />
            <IntegrationStatus ok={incident.siem_dispatched} label="SIEM Event" />
            <IntegrationStatus ok={incident.veeamone_reported} label="VeeamONE" />
            <IntegrationStatus ok={incident.notifications_sent} label="Notifications" />
            {incident.backup_job_id && (
              <p className="text-xs text-gray-400 mt-2">Backup job: {incident.backup_job_id}</p>
            )}
            {incident.soar_incident_id && (
              <p className="text-xs text-gray-400">SOAR ID: {incident.soar_incident_id}</p>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Incidents</h1>
          <p className="text-sm text-gray-500 mt-1">
            {activeIncidents.length} active &bull; {resolvedIncidents.length} resolved
          </p>
        </div>
      </div>

      {isLoading && <p className="text-sm text-gray-400">Loading incidents...</p>}

      {!isLoading && incidents.length === 0 && (
        <div className="bg-white rounded-xl shadow p-10 text-center">
          <p className="text-gray-500 text-sm">
            No incidents. Threat scanner is watching the environment.
          </p>
        </div>
      )}

      {activeIncidents.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-sm font-semibold text-red-600 uppercase tracking-wide">
            Active Incidents
          </h2>
          {activeIncidents.map(renderIncident)}
        </div>
      )}

      {resolvedIncidents.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide">
            Resolved Incidents
          </h2>
          {resolvedIncidents.map(renderIncident)}
        </div>
      )}

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

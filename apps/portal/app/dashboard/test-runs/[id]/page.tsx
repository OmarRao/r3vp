"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api";

interface WorkflowStep {
  id: string;
  name: string;
  status: "passed" | "failed" | "running" | "pending";
  started_at: string | null;
  ended_at: string | null;
  detail: string | null;
}

interface TestRun {
  id: string;
  workload_id: string;
  workload_name: string | null;
  status: "passed" | "failed" | "running" | "pending";
  triggered_at: string;
  rto_target_mins: number | null;
  rpo_target_mins: number | null;
  actual_rto_mins: number | null;
  actual_rpo_mins: number | null;
  readiness_score: number | null;
  steps: WorkflowStep[];
}

const resultBadge: Record<string, string> = {
  passed: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
  running: "bg-blue-100 text-blue-800",
  pending: "bg-yellow-100 text-yellow-800",
};

function stepDuration(step: WorkflowStep): string {
  if (step.started_at && step.ended_at) {
    const diffMs = new Date(step.ended_at).getTime() - new Date(step.started_at).getTime();
    const diffSecs = Math.round(diffMs / 1000);
    if (diffSecs < 60) return `${diffSecs}s`;
    return `${Math.round(diffSecs / 60)}m ${diffSecs % 60}s`;
  }
  if (step.status === "running") return "in progress...";
  return "—";
}

function StepIcon({ status }: { status: WorkflowStep["status"] }) {
  if (status === "passed") {
    return (
      <span className="flex-shrink-0 w-6 h-6 rounded-full bg-green-500 flex items-center justify-center text-white text-xs font-bold">
        ✓
      </span>
    );
  }
  if (status === "failed") {
    return (
      <span className="flex-shrink-0 w-6 h-6 rounded-full bg-red-500 flex items-center justify-center text-white text-xs font-bold">
        ✗
      </span>
    );
  }
  if (status === "running") {
    return (
      <span className="flex-shrink-0 w-6 h-6 rounded-full border-2 border-blue-500 border-t-transparent animate-spin" />
    );
  }
  return (
    <span className="flex-shrink-0 w-6 h-6 rounded-full bg-gray-300" />
  );
}

function MetricCell({
  label,
  target,
  actual,
}: {
  label: string;
  target: number | null;
  actual: number | null;
}) {
  const isOver = target != null && actual != null && actual > target;
  const isUnder = target != null && actual != null && actual <= target;
  return (
    <div>
      <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
      <p className="text-2xl font-bold mt-1">
        <span className={isOver ? "text-red-600" : isUnder ? "text-green-600" : "text-gray-800"}>
          {actual != null ? `${actual} min` : "—"}
        </span>
        {target != null && (
          <span className="text-sm text-gray-400 font-normal ml-2">target: {target} min</span>
        )}
      </p>
    </div>
  );
}

const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "";

export default function TestRunDetailPage() {
  const { id } = useParams<{ id: string }>();

  const { data: run, isLoading } = useQuery<TestRun>({
    queryKey: ["test-run", id],
    queryFn: () => api.get(`/v1/test-runs/${id}`).then((r) => r.data),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "running" || status === "pending" ? 5000 : false;
    },
  });

  if (isLoading) {
    return (
      <div className="p-6 flex items-center justify-center">
        <div className="animate-spin border-4 rounded-full w-8 h-8 border-green-500 border-t-transparent" />
      </div>
    );
  }

  if (!run) {
    return (
      <div className="p-6">
        <p className="text-gray-500">Test run not found.</p>
        <Link href="/dashboard" className="text-veeam-green text-sm mt-2 inline-block">
          &larr; Back to Dashboard
        </Link>
      </div>
    );
  }

  const isLive = run.status === "running" || run.status === "pending";
  const shortId = run.id.slice(0, 8);
  const workloadLabel = run.workload_name ?? run.workload_id;

  return (
    <div className="p-6 space-y-6">
      {/* Back link */}
      <Link href="/dashboard" className="text-sm text-veeam-green hover:underline">
        &larr; Back to Dashboard
      </Link>

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-bold text-gray-900">
              Run <span className="font-mono text-lg">{shortId}...</span>
            </h1>
            <span
              className={`px-2 py-0.5 rounded-full text-xs font-medium ${resultBadge[run.status] ?? "bg-gray-100 text-gray-600"}`}
            >
              {run.status}
            </span>
            {isLive && (
              <span className="flex items-center gap-1.5 text-xs text-green-600 font-medium">
                <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                Live
              </span>
            )}
          </div>
          <p className="text-sm text-gray-500">
            {workloadLabel} &mdash; triggered {new Date(run.triggered_at).toLocaleString()}
          </p>
        </div>

        {apiBase ? (
          <a
            href={`${apiBase}/v1/test-runs/${id}/report`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-block bg-veeam-green text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-700 transition-colors"
          >
            Download Evidence Report (PDF)
          </a>
        ) : (
          <button
            disabled
            className="inline-block bg-gray-200 text-gray-400 px-4 py-2 rounded-lg text-sm font-medium cursor-not-allowed"
          >
            Report available after test completes
          </button>
        )}
      </div>

      {/* Result Summary */}
      <div className="bg-white rounded-xl shadow p-5">
        <h2 className="text-lg font-semibold mb-4">Result Summary</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          <MetricCell label="RTO" target={run.rto_target_mins} actual={run.actual_rto_mins} />
          <MetricCell label="RPO" target={run.rpo_target_mins} actual={run.actual_rpo_mins} />
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wide">Readiness Score</p>
            <p
              className={`text-4xl font-bold mt-1 ${
                run.readiness_score != null && run.readiness_score >= 80
                  ? "text-green-600"
                  : run.readiness_score != null
                  ? "text-red-600"
                  : "text-gray-400"
              }`}
            >
              {run.readiness_score != null ? run.readiness_score : "—"}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500 uppercase tracking-wide">Status</p>
            <div className="mt-2">
              <span
                className={`px-2 py-0.5 rounded-full text-sm font-medium ${resultBadge[run.status] ?? "bg-gray-100 text-gray-600"}`}
              >
                {run.status}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Workflow Steps */}
      {run.steps && run.steps.length > 0 && (
        <div className="bg-white rounded-xl shadow p-5">
          <h2 className="text-lg font-semibold mb-4">Workflow Steps</h2>
          <div className="relative">
            {/* Vertical connecting line */}
            <div className="absolute left-3 top-3 bottom-3 w-0.5 bg-gray-200" />
            <ol className="space-y-4">
              {run.steps.map((step) => (
                <li key={step.id} className="flex items-start gap-3 relative">
                  <StepIcon status={step.status} />
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-baseline gap-2">
                      <span className="text-sm font-semibold text-gray-900">{step.name}</span>
                      <span className="text-xs text-gray-400">{stepDuration(step)}</span>
                      {step.started_at && (
                        <span className="text-xs text-gray-400">
                          started {new Date(step.started_at).toLocaleTimeString()}
                        </span>
                      )}
                    </div>
                    {step.detail && (
                      <p className="text-xs text-gray-500 mt-0.5">{step.detail}</p>
                    )}
                  </div>
                </li>
              ))}
            </ol>
          </div>
        </div>
      )}
    </div>
  );
}

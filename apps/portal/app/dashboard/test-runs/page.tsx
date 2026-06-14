"use client";

import Link from "next/link";

export default function TestRunsPage() {
  return (
    <div className="p-6 space-y-4">
      <h1 className="text-2xl font-bold text-gray-900">Test Runs</h1>
      <div className="bg-white rounded-xl shadow p-5">
        <p className="text-gray-600">
          Navigate to a workload to trigger and view test runs.
        </p>
      </div>
      <Link href="/dashboard" className="text-sm text-veeam-green hover:underline inline-block">
        &larr; Back to Dashboard
      </Link>
    </div>
  );
}

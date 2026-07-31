"use client";
/*
 * Copyright (c) 2026 Omar Rao
 * SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
 * This file is available under the GNU Affero General Public License v3.0
 * or under a separate commercial license.
 */


import Link from "next/link";

export default function TestRunsPage() {
  return (
    <div className="p-6 space-y-4">
      <h1 className="text-2xl font-bold text-content">Test Runs</h1>
      <div className="bg-surface rounded-xl shadow p-5">
        <p className="text-content-muted">
          Navigate to a workload to trigger and view test runs.
        </p>
      </div>
      <Link href="/dashboard" className="text-sm text-veeam-green hover:underline inline-block">
        &larr; Back to Dashboard
      </Link>
    </div>
  );
}

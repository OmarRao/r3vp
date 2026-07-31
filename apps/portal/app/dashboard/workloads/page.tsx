"use client";
/*
 * Copyright (c) 2026 Omar Rao
 * SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
 * This file is available under the GNU Affero General Public License v3.0
 * or under a separate commercial license.
 */


import Link from "next/link";
import { WorkloadGrid } from "@/components/workload-grid";

export default function WorkloadsPage() {
  return (
    <div className="p-6 space-y-4">
      <h1 className="text-2xl font-bold text-content">Workloads</h1>
      <div className="bg-surface rounded-xl shadow p-5">
        <p className="text-content-muted mb-4">
          Select a workload to view its recovery targets, run tests, and review test-run history.
        </p>
        <WorkloadGrid />
      </div>
      <Link href="/dashboard" className="text-sm text-veeam-green hover:underline inline-block">
        &larr; Back to Dashboard
      </Link>
    </div>
  );
}

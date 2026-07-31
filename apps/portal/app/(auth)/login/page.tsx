/*
 * Copyright (c) 2026 Omar Rao
 * SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
 * This file is available under the GNU Affero General Public License v3.0
 * or under a separate commercial license.
 */

import { redirect } from "next/navigation";

export default function LoginPage() {
  // Auth0 SDK handles /api/auth/login - this page just redirects there
  redirect("/api/auth/login");
}

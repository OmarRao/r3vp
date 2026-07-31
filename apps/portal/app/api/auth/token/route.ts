/*
 * Copyright (c) 2026 Omar Rao
 * SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
 * This file is available under the GNU Affero General Public License v3.0
 * or under a separate commercial license.
 */

import { getAccessToken } from "@auth0/nextjs-auth0";
import { NextResponse } from "next/server";

export async function GET() {
  try {
    const { accessToken } = await getAccessToken();
    return NextResponse.json({ accessToken });
  } catch {
    return NextResponse.json({ accessToken: null }, { status: 401 });
  }
}

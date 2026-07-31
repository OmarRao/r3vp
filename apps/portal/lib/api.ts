/*
 * Copyright (c) 2026 Omar Rao
 * SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
 * This file is available under the GNU Affero General Public License v3.0
 * or under a separate commercial license.
 */

import axios from "axios";

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
  withCredentials: true,
});

// Attach Auth0 access token from the session on every request
api.interceptors.request.use(async (config) => {
  if (typeof window !== "undefined") {
    try {
      const resp = await fetch("/api/auth/token");
      if (resp.ok) {
        const { accessToken } = await resp.json();
        if (accessToken) {
          config.headers.Authorization = `Bearer ${accessToken}`;
        }
      }
    } catch {
      // unauthenticated - middleware will redirect
    }
  }
  return config;
});

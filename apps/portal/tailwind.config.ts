/*
 * Copyright (c) 2026 Omar Rao
 * SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
 * This file is available under the GNU Affero General Public License v3.0
 * or under a separate commercial license.
 */

import type { Config } from "tailwindcss";

const withOpacity = (v: string) => `rgb(var(${v}) / <alpha-value>)`;

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Veeam brand palette
        veeam: {
          green: "#00B336",
          dark: "#1A1A2E",
          gray: "#F4F6F8",
        },
        // Semantic tokens (theme-aware; defined in globals.css)
        bg: withOpacity("--color-bg"),
        surface: withOpacity("--color-surface"),
        "surface-2": withOpacity("--color-surface-2"),
        content: withOpacity("--color-content"),
        "content-muted": withOpacity("--color-content-muted"),
        border: withOpacity("--color-border"),
        accent: withOpacity("--color-accent"),
        "accent-content": withOpacity("--color-accent-content"),
      },
    },
  },
  plugins: [],
};

export default config;

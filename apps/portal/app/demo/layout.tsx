/*
 * Copyright (c) 2026 Omar Rao
 * SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
 * This file is available under the GNU Affero General Public License v3.0
 * or under a separate commercial license.
 */

import type { ReactNode } from "react";
import { FirebaseAuthProvider } from "@/context/firebase-auth-context";

export const metadata = {
  title: "R3VP Demo",
  description: "Live demo of the R3VP platform. Sign in with Google to explore.",
};

export default function DemoLayout({ children }: { children: ReactNode }) {
  return <FirebaseAuthProvider>{children}</FirebaseAuthProvider>;
}

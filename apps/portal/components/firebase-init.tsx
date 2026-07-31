"use client";
/*
 * Copyright (c) 2026 Omar Rao
 * SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
 * This file is available under the GNU Affero General Public License v3.0
 * or under a separate commercial license.
 */


import { useEffect } from "react";
import { useUser } from "@auth0/nextjs-auth0/client";
import { initFirebase } from "@/lib/firebase";
import { trackLogin } from "@/lib/track";

export function FirebaseInit() {
  const { user } = useUser();

  useEffect(() => {
    initFirebase();
  }, []);

  useEffect(() => {
    if (user?.email) {
      trackLogin(user.email);
    }
  }, [user?.email]);

  return null;
}

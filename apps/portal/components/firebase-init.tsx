"use client";

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

"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import {
  onAuthStateChanged,
  signOut as firebaseSignOut,
  type User,
} from "firebase/auth";
import { getFirebaseAuth } from "@/lib/firebase";

interface FirebaseAuthContextValue {
  user: User | null;
  loading: boolean;
  signOut: () => Promise<void>;
}

const FirebaseAuthContext = createContext<FirebaseAuthContextValue>({
  user: null,
  loading: true,
  signOut: async () => {},
});

export function FirebaseAuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const auth = getFirebaseAuth();
    if (!auth) {
      setLoading(false);
      return;
    }
    const unsub = onAuthStateChanged(auth, (u) => {
      setUser(u);
      setLoading(false);
    });
    return unsub;
  }, []);

  async function signOut() {
    const auth = getFirebaseAuth();
    if (auth) await firebaseSignOut(auth);
  }

  return (
    <FirebaseAuthContext.Provider value={{ user, loading, signOut }}>
      {children}
    </FirebaseAuthContext.Provider>
  );
}

export function useFirebaseAuth() {
  return useContext(FirebaseAuthContext);
}

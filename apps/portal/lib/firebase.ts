import { initializeApp, getApps, type FirebaseApp } from "firebase/app";
import { getAnalytics, type Analytics } from "firebase/analytics";
import { getAuth, type Auth } from "firebase/auth";

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
  measurementId: process.env.NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID,
};

let app: FirebaseApp | undefined;
let analytics: Analytics | undefined;
let auth: Auth | undefined;

export function initFirebase(): { app: FirebaseApp; analytics: Analytics; auth: Auth } | null {
  if (typeof window === "undefined") return null;
  if (!firebaseConfig.apiKey) return null;

  if (!app) {
    app = getApps().length === 0 ? initializeApp(firebaseConfig) : getApps()[0];
  }
  if (!analytics) {
    analytics = getAnalytics(app);
  }
  if (!auth) {
    auth = getAuth(app);
  }
  return { app, analytics, auth };
}

export function getFirebaseAuth(): Auth | null {
  const fb = initFirebase();
  return fb ? fb.auth : null;
}

export { analytics, auth };

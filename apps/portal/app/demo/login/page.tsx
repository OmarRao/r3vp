"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  GoogleAuthProvider,
  signInWithPopup,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
} from "firebase/auth";
import { getFirebaseAuth } from "@/lib/firebase";
import { useFirebaseAuth } from "@/context/firebase-auth-context";

export default function DemoLoginPage() {
  const { user, loading } = useFirebaseAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!loading && user) router.replace("/demo");
  }, [user, loading, router]);

  async function handleGoogle() {
    const auth = getFirebaseAuth();
    if (!auth) return setError("Firebase is not configured. Add NEXT_PUBLIC_FIREBASE_* env vars.");
    setBusy(true);
    setError("");
    try {
      await signInWithPopup(auth, new GoogleAuthProvider());
      router.replace("/demo");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Google sign-in failed.");
    } finally {
      setBusy(false);
    }
  }

  async function handleEmailAuth(e: React.FormEvent) {
    e.preventDefault();
    const auth = getFirebaseAuth();
    if (!auth) return setError("Firebase is not configured. Add NEXT_PUBLIC_FIREBASE_* env vars.");
    setBusy(true);
    setError("");
    try {
      if (mode === "signin") {
        await signInWithEmailAndPassword(auth, email, password);
      } else {
        await createUserWithEmailAndPassword(auth, email, password);
      }
      router.replace("/demo");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Authentication failed.");
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return (
      <div style={{ display: "flex", height: "100vh", alignItems: "center", justifyContent: "center", background: "#F8FAFC", fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" }}>
        <p style={{ color: "#94A3B8", fontSize: 14 }}>Loading...</p>
      </div>
    );
  }

  return (
    <div style={{
      minHeight: "100vh", background: "#F8FAFC", display: "flex", alignItems: "center",
      justifyContent: "center", fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
      padding: "24px",
    }}>
      <div style={{ width: "100%", maxWidth: 400 }}>
        {/* Logo */}
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <div style={{ fontSize: 32, fontWeight: 800, color: "#0F172A", letterSpacing: "-1px", marginBottom: 4 }}>
            R<span style={{ color: "#00B336" }}>3</span>VP
          </div>
          <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "2px", color: "#00B336" }}>
            DEMO ENVIRONMENT
          </div>
          <p style={{ marginTop: 12, fontSize: 13, color: "#64748B", lineHeight: 1.5 }}>
            Sign in to explore the R3VP platform with sample recovery validation data.
          </p>
        </div>

        {/* Card */}
        <div style={{
          background: "#fff", border: "1px solid #E2E8F0", borderRadius: 12,
          padding: "28px 28px 24px", boxShadow: "0 1px 3px rgba(0,0,0,0.08)",
        }}>
          <h2 style={{ fontSize: 15, fontWeight: 700, color: "#0F172A", marginBottom: 20 }}>
            {mode === "signin" ? "Sign in to demo" : "Create demo account"}
          </h2>

          {/* Google */}
          <button
            onClick={handleGoogle}
            disabled={busy}
            style={{
              width: "100%", display: "flex", alignItems: "center", justifyContent: "center",
              gap: 10, padding: "10px 16px", border: "1px solid #E2E8F0", borderRadius: 8,
              background: "#fff", cursor: busy ? "not-allowed" : "pointer", fontSize: 13,
              fontWeight: 600, color: "#0F172A", marginBottom: 18, opacity: busy ? 0.6 : 1,
              fontFamily: "inherit",
            }}
          >
            <svg width="18" height="18" viewBox="0 0 18 18">
              <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.875 2.684-6.615z" fill="#4285F4"/>
              <path d="M9 18c2.43 0 4.467-.806 5.956-2.184l-2.908-2.258c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18z" fill="#34A853"/>
              <path d="M3.964 10.707A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.707V4.961H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.039l3.007-2.332z" fill="#FBBC05"/>
              <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.961L3.964 7.293C4.672 5.163 6.656 3.58 9 3.58z" fill="#EA4335"/>
            </svg>
            Continue with Google
          </button>

          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 18 }}>
            <div style={{ flex: 1, height: 1, background: "#E2E8F0" }} />
            <span style={{ fontSize: 11, color: "#94A3B8", fontWeight: 600 }}>OR</span>
            <div style={{ flex: 1, height: 1, background: "#E2E8F0" }} />
          </div>

          {/* Email / Password */}
          <form onSubmit={handleEmailAuth}>
            <div style={{ marginBottom: 12 }}>
              <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: "#374151", marginBottom: 5 }}>
                Email address
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                placeholder="you@example.com"
                style={{
                  width: "100%", padding: "9px 12px", border: "1px solid #D1D5DB", borderRadius: 7,
                  fontSize: 13, color: "#0F172A", background: "#fff", outline: "none",
                  fontFamily: "inherit", boxSizing: "border-box",
                }}
              />
            </div>
            <div style={{ marginBottom: 18 }}>
              <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: "#374151", marginBottom: 5 }}>
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
                placeholder="Min 6 characters"
                style={{
                  width: "100%", padding: "9px 12px", border: "1px solid #D1D5DB", borderRadius: 7,
                  fontSize: 13, color: "#0F172A", background: "#fff", outline: "none",
                  fontFamily: "inherit", boxSizing: "border-box",
                }}
              />
            </div>

            {error && (
              <div style={{
                background: "#FFF1F2", border: "1px solid #FECACA", borderRadius: 7,
                padding: "9px 12px", fontSize: 12, color: "#DC2626", marginBottom: 14,
              }}>
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={busy}
              style={{
                width: "100%", padding: "10px 16px", background: "#00B336", color: "#fff",
                border: "none", borderRadius: 8, fontSize: 13, fontWeight: 700,
                cursor: busy ? "not-allowed" : "pointer", opacity: busy ? 0.7 : 1,
                fontFamily: "inherit",
              }}
            >
              {busy ? "Please wait..." : mode === "signin" ? "Sign in" : "Create account"}
            </button>
          </form>
        </div>

        {/* Toggle mode */}
        <p style={{ textAlign: "center", fontSize: 12, color: "#64748B", marginTop: 16 }}>
          {mode === "signin" ? "No account yet?" : "Already have an account?"}{" "}
          <button
            onClick={() => { setMode(mode === "signin" ? "signup" : "signin"); setError(""); }}
            style={{ background: "none", border: "none", color: "#00B336", fontWeight: 700, cursor: "pointer", fontSize: 12, fontFamily: "inherit" }}
          >
            {mode === "signin" ? "Create one" : "Sign in"}
          </button>
        </p>

        <p style={{ textAlign: "center", fontSize: 11, color: "#94A3B8", marginTop: 24, lineHeight: 1.5 }}>
          Demo data only. No real infrastructure is connected.
          <br />
          Built by{" "}
          <a href="https://www.linkedin.com/in/omarrao/" style={{ color: "#00B336" }}>Omar Rao</a>
          {" "} - Engineer, Data Resilience
        </p>
      </div>
    </div>
  );
}

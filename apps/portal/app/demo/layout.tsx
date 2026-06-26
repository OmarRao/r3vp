import type { ReactNode } from "react";
import { FirebaseAuthProvider } from "@/context/firebase-auth-context";

export const metadata = {
  title: "R3VP Demo",
  description: "Live demo of the R3VP platform. Sign in with Google to explore.",
};

export default function DemoLayout({ children }: { children: ReactNode }) {
  return <FirebaseAuthProvider>{children}</FirebaseAuthProvider>;
}

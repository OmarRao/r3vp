import { redirect } from "next/navigation";

export default function LoginPage() {
  // Auth0 SDK handles /api/auth/login — this page just redirects there
  redirect("/api/auth/login");
}

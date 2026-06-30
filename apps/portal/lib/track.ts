import { logEvent } from "firebase/analytics";
import { initFirebase } from "./firebase";

type EventName =
  | "login"
  | "logout"
  | "page_view"
  | "test_run_started"
  | "evidence_downloaded"
  | "compliance_report_generated"
  | "runbook_executed"
  | "appliance_registered"
  | "workload_discovered"
  | "api_key_created";

export function track(event: EventName, params?: Record<string, string | number | boolean>) {
  const fb = initFirebase();
  if (!fb) return;
  // Cast to the generic custom-event overload (string name) to avoid clashing
  // with firebase's typed standard-event overloads.
  logEvent(fb.analytics, event as string, params);
}

export function trackLogin(userEmail: string, method: string = "auth0") {
  track("login", { method, email_domain: userEmail.split("@")[1] ?? "unknown" });
}

export function trackPageView(pageName: string) {
  track("page_view", { page_name: pageName });
}

"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useFirebaseAuth } from "@/context/firebase-auth-context";

/* ------------------------------------------------------------------ */
/* Mock data                                                            */
/* ------------------------------------------------------------------ */

const WORKLOADS = [
  { id: 1, name: "dc01.acme.local", provider: "VMware", type: "Domain Controller", rto_target: 60, rto_actual: 42, rpo_hours: 4, status: "pass", last_tested: "2h ago" },
  { id: 2, name: "sql-prod-01", provider: "VMware", type: "SQL Server", rto_target: 120, rto_actual: 98, rpo_hours: 2, status: "pass", last_tested: "6h ago" },
  { id: 3, name: "exchange-01", provider: "Hyper-V", type: "Exchange", rto_target: 180, rto_actual: 204, rpo_hours: 8, status: "fail", last_tested: "1d ago" },
  { id: 4, name: "erp-app-prod", provider: "Azure", type: "App Server", rto_target: 90, rto_actual: 71, rpo_hours: 4, status: "pass", last_tested: "3h ago" },
  { id: 5, name: "web-cluster-01", provider: "AWS", type: "Web Server", rto_target: 30, rto_actual: 28, rpo_hours: 1, status: "pass", last_tested: "1h ago" },
  { id: 6, name: "file-server-02", provider: "VMware", type: "File Server", rto_target: 240, rto_actual: null, rpo_hours: 24, status: "untested", last_tested: "Never" },
  { id: 7, name: "backup-proxy-01", provider: "VMware", type: "Backup Proxy", rto_target: 60, rto_actual: 55, rpo_hours: 4, status: "pass", last_tested: "12h ago" },
  { id: 8, name: "k8s-worker-03", provider: "GCP", type: "Kubernetes", rto_target: 45, rto_actual: 38, rpo_hours: 2, status: "pass", last_tested: "4h ago" },
];

const TEST_RUNS = [
  { id: "TR-1042", workload: "dc01.acme.local", provider: "VMware", status: "pass", rto: "42m", started: "2h ago", duration: "14m" },
  { id: "TR-1041", workload: "sql-prod-01", provider: "VMware", status: "pass", rto: "98m", started: "6h ago", duration: "22m" },
  { id: "TR-1040", workload: "exchange-01", provider: "Hyper-V", status: "fail", rto: "204m", started: "1d ago", duration: "31m" },
  { id: "TR-1039", workload: "erp-app-prod", provider: "Azure", status: "pass", rto: "71m", started: "3h ago", duration: "18m" },
  { id: "TR-1038", workload: "web-cluster-01", provider: "AWS", status: "pass", rto: "28m", started: "1h ago", duration: "9m" },
];

const ALERTS = [
  { id: 1, severity: "high", message: "exchange-01 RTO exceeded target by 24 minutes", time: "1d ago" },
  { id: 2, severity: "medium", message: "file-server-02 has not been tested in 30+ days", time: "2d ago" },
  { id: 3, severity: "low", message: "RPO for sql-prod-01 approaching 2h threshold", time: "8h ago" },
];

/* ------------------------------------------------------------------ */
/* Style helpers                                                        */
/* ------------------------------------------------------------------ */

const colors = {
  bg: "#F8FAFC", surface: "#FFFFFF", border: "#E2E8F0",
  text1: "#0F172A", text2: "#475569", text3: "#94A3B8",
  green: "#00B336", greenBg: "#F0FDF4", greenBorder: "#BBF7D0", greenText: "#15803D",
  amber: "#D97706", amberBg: "#FFFBEB",
  red: "#DC2626", redBg: "#FFF1F2", redBorder: "#FECACA",
  blue: "#2563EB", blueBg: "#EFF6FF",
  sidebar: "#0F172A",
};

function Badge({ color, children }: { color: "green" | "red" | "amber" | "blue" | "gray"; children: React.ReactNode }) {
  const map = {
    green: { bg: colors.greenBg, text: colors.greenText, border: colors.greenBorder },
    red: { bg: colors.redBg, text: colors.red, border: colors.redBorder },
    amber: { bg: colors.amberBg, text: colors.amber, border: "#FDE68A" },
    blue: { bg: colors.blueBg, text: colors.blue, border: "#BFDBFE" },
    gray: { bg: "#F1F5F9", text: "#64748B", border: "#E2E8F0" },
  };
  const s = map[color];
  return (
    <span style={{ display: "inline-flex", alignItems: "center", padding: "2px 8px", borderRadius: 99, fontSize: 10, fontWeight: 700, background: s.bg, color: s.text, border: `1px solid ${s.border}`, whiteSpace: "nowrap" }}>
      {children}
    </span>
  );
}

function KpiCard({ label, value, sub, accent }: { label: string; value: string; sub?: string; accent?: string }) {
  return (
    <div style={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 10, padding: "14px 18px", boxShadow: "0 1px 2px rgba(0,0,0,0.04)", flex: 1 }}>
      <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.8px", color: colors.text3, marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 26, fontWeight: 800, color: accent || colors.text1, lineHeight: 1, letterSpacing: "-0.5px" }}>{value}</div>
      {sub && <div style={{ fontSize: 11, color: colors.text3, marginTop: 4 }}>{sub}</div>}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Sidebar nav items                                                    */
/* ------------------------------------------------------------------ */

type NavSection = { section: string; items: { icon: string; label: string; key: string }[] };
const NAV: NavSection[] = [
  { section: "Overview", items: [
    { icon: "⬡", label: "Dashboard", key: "dashboard" },
    { icon: "◈", label: "Workloads", key: "workloads" },
    { icon: "▶", label: "Test Runs", key: "test-runs" },
  ]},
  { section: "Security", items: [
    { icon: "🔒", label: "Evidence Vault", key: "evidence" },
    { icon: "☑", label: "Compliance", key: "compliance" },
    { icon: "⚡", label: "Continuous Val.", key: "continuous" },
    { icon: "⚠", label: "Threat Scanner", key: "threats" },
  ]},
  { section: "Operations", items: [
    { icon: "🖥", label: "Fleet", key: "fleet" },
    { icon: "📋", label: "Runbooks", key: "runbooks" },
    { icon: "📊", label: "Reports", key: "reports" },
    { icon: "🤖", label: "AI Insights", key: "insights" },
  ]},
  { section: "Account", items: [
    { icon: "👥", label: "Team", key: "team" },
    { icon: "🔑", label: "API Keys", key: "apikeys" },
    { icon: "📈", label: "User Analytics", key: "analytics" },
  ]},
];

/* ------------------------------------------------------------------ */
/* Tab content renderers                                                */
/* ------------------------------------------------------------------ */

function DashboardTab() {
  const pass = WORKLOADS.filter((w) => w.status === "pass").length;
  const fail = WORKLOADS.filter((w) => w.status === "fail").length;
  const untested = WORKLOADS.filter((w) => w.status === "untested").length;
  const passRate = Math.round((pass / (WORKLOADS.length - untested)) * 100);

  return (
    <div>
      {/* KPI row */}
      <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
        <KpiCard label="Readiness Score" value="87" sub="Out of 100" accent={colors.green} />
        <KpiCard label="Workloads Protected" value={`${WORKLOADS.length - untested}/${WORKLOADS.length}`} sub={`${untested} untested`} />
        <KpiCard label="Pass Rate (30d)" value={`${passRate}%`} sub="5 runs this week" />
        <KpiCard label="RTO Compliance" value="86%" sub="6 of 7 within target" />
        <KpiCard label="Active Alerts" value={String(ALERTS.length)} sub="1 high, 1 med" accent={ALERTS.length > 0 ? colors.amber : undefined} />
      </div>

      {/* Alerts banner */}
      {ALERTS.length > 0 && (
        <div style={{ background: colors.amberBg, border: `1px solid #FDE68A`, borderRadius: 10, padding: "12px 16px", marginBottom: 20 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: colors.amber, marginBottom: 8 }}>Active Alerts</div>
          {ALERTS.map((a) => (
            <div key={a.id} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4, fontSize: 12, color: colors.text2 }}>
              <Badge color={a.severity === "high" ? "red" : a.severity === "medium" ? "amber" : "gray"}>
                {a.severity.toUpperCase()}
              </Badge>
              <span>{a.message}</span>
              <span style={{ marginLeft: "auto", color: colors.text3, fontSize: 11 }}>{a.time}</span>
            </div>
          ))}
        </div>
      )}

      {/* Recent test runs */}
      <div style={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 10, boxShadow: "0 1px 2px rgba(0,0,0,0.04)" }}>
        <div style={{ padding: "14px 18px", borderBottom: `1px solid ${colors.border}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ fontSize: 12, fontWeight: 700, color: colors.text1 }}>Recent Test Runs</span>
          <span style={{ fontSize: 11, color: colors.green, fontWeight: 600, cursor: "pointer" }}>View all</span>
        </div>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "#F8FAFC" }}>
              {["Run ID", "Workload", "Provider", "Status", "RTO", "Started", "Duration"].map((h) => (
                <th key={h} style={{ padding: "8px 16px", textAlign: "left", fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.5px", color: colors.text3, borderBottom: `1px solid ${colors.border}` }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {TEST_RUNS.map((r, i) => (
              <tr key={r.id} style={{ borderBottom: i < TEST_RUNS.length - 1 ? `1px solid ${colors.border}` : "none" }}>
                <td style={{ padding: "10px 16px", fontSize: 12, fontFamily: "monospace", color: colors.blue }}>{r.id}</td>
                <td style={{ padding: "10px 16px", fontSize: 12, color: colors.text1, fontWeight: 600 }}>{r.workload}</td>
                <td style={{ padding: "10px 16px" }}><Badge color="blue">{r.provider}</Badge></td>
                <td style={{ padding: "10px 16px" }}><Badge color={r.status === "pass" ? "green" : "red"}>{r.status.toUpperCase()}</Badge></td>
                <td style={{ padding: "10px 16px", fontSize: 12, color: colors.text1 }}>{r.rto}</td>
                <td style={{ padding: "10px 16px", fontSize: 12, color: colors.text3 }}>{r.started}</td>
                <td style={{ padding: "10px 16px", fontSize: 12, color: colors.text3 }}>{r.duration}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function WorkloadsTab() {
  return (
    <div>
      <div style={{ display: "flex", gap: 12, marginBottom: 20 }}>
        <KpiCard label="Total Workloads" value={String(WORKLOADS.length)} sub="Across 5 providers" />
        <KpiCard label="Tested" value={String(WORKLOADS.filter((w) => w.status !== "untested").length)} sub="Last 30 days" />
        <KpiCard label="Passing" value={String(WORKLOADS.filter((w) => w.status === "pass").length)} accent={colors.green} />
        <KpiCard label="Failing" value={String(WORKLOADS.filter((w) => w.status === "fail").length)} accent={colors.red} />
      </div>
      <div style={{ background: colors.surface, border: `1px solid ${colors.border}`, borderRadius: 10, boxShadow: "0 1px 2px rgba(0,0,0,0.04)" }}>
        <div style={{ padding: "14px 18px", borderBottom: `1px solid ${colors.border}` }}>
          <span style={{ fontSize: 12, fontWeight: 700, color: colors.text1 }}>Workload Inventory</span>
        </div>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "#F8FAFC" }}>
              {["Workload", "Type", "Provider", "RTO Target", "RTO Actual", "RPO", "Status", "Last Tested"].map((h) => (
                <th key={h} style={{ padding: "8px 14px", textAlign: "left", fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.5px", color: colors.text3, borderBottom: `1px solid ${colors.border}` }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {WORKLOADS.map((w, i) => (
              <tr key={w.id} style={{ borderBottom: i < WORKLOADS.length - 1 ? `1px solid ${colors.border}` : "none" }}>
                <td style={{ padding: "10px 14px", fontSize: 12, fontWeight: 600, color: colors.text1 }}>{w.name}</td>
                <td style={{ padding: "10px 14px", fontSize: 11, color: colors.text2 }}>{w.type}</td>
                <td style={{ padding: "10px 14px" }}><Badge color="blue">{w.provider}</Badge></td>
                <td style={{ padding: "10px 14px", fontSize: 12, color: colors.text2 }}>{w.rto_target}m</td>
                <td style={{ padding: "10px 14px", fontSize: 12, color: w.rto_actual && w.rto_actual > w.rto_target ? colors.red : colors.text1 }}>
                  {w.rto_actual ? `${w.rto_actual}m` : "-"}
                </td>
                <td style={{ padding: "10px 14px", fontSize: 12, color: colors.text2 }}>{w.rpo_hours}h</td>
                <td style={{ padding: "10px 14px" }}>
                  <Badge color={w.status === "pass" ? "green" : w.status === "fail" ? "red" : "gray"}>
                    {w.status.toUpperCase()}
                  </Badge>
                </td>
                <td style={{ padding: "10px 14px", fontSize: 11, color: colors.text3 }}>{w.last_tested}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function PlaceholderTab({ label }: { label: string }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: 320, color: colors.text3, gap: 12 }}>
      <div style={{ fontSize: 36 }}>🔒</div>
      <div style={{ fontSize: 14, fontWeight: 700, color: colors.text2 }}>{label}</div>
      <div style={{ fontSize: 12, color: colors.text3 }}>Available in the full platform connected to your environment.</div>
    </div>
  );
}

const TAB_CONTENT: Record<string, React.ReactNode> = {
  dashboard: <DashboardTab />,
  workloads: <WorkloadsTab />,
  "test-runs": <PlaceholderTab label="Test Runs" />,
  evidence: <PlaceholderTab label="Evidence Vault" />,
  compliance: <PlaceholderTab label="Compliance Frameworks" />,
  continuous: <PlaceholderTab label="Continuous Validation" />,
  threats: <PlaceholderTab label="Threat Scanner" />,
  fleet: <PlaceholderTab label="Fleet Management" />,
  runbooks: <PlaceholderTab label="Runbooks" />,
  reports: <PlaceholderTab label="Reports" />,
  insights: <PlaceholderTab label="AI Insights" />,
  team: <PlaceholderTab label="Team Management" />,
  apikeys: <PlaceholderTab label="API Keys" />,
  analytics: <PlaceholderTab label="User Analytics" />,
};

const TAB_LABELS: Record<string, string> = {
  dashboard: "Recovery Readiness Dashboard",
  workloads: "Workloads",
  "test-runs": "Test Runs",
  evidence: "Evidence Vault",
  compliance: "Compliance Frameworks",
  continuous: "Continuous Validation",
  threats: "Threat Scanner",
  fleet: "Fleet Management",
  runbooks: "DR Runbooks",
  reports: "Reports",
  insights: "AI Insights",
  team: "Team Management",
  apikeys: "API Keys",
  analytics: "User Analytics",
};

/* ------------------------------------------------------------------ */
/* Main demo page                                                       */
/* ------------------------------------------------------------------ */

export default function DemoPage() {
  const { user, loading, signOut } = useFirebaseAuth();
  const router = useRouter();
  const [activeTab, setActiveTab] = useState("dashboard");

  useEffect(() => {
    if (!loading && !user) router.replace("/demo/login");
  }, [user, loading, router]);

  if (loading || !user) {
    return (
      <div style={{ display: "flex", height: "100vh", alignItems: "center", justifyContent: "center", background: colors.bg, fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" }}>
        <p style={{ color: colors.text3, fontSize: 14 }}>Loading demo...</p>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden", fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif", background: colors.bg, color: colors.text1, fontSize: 13 }}>
      {/* Sidebar */}
      <div style={{ width: 220, flexShrink: 0, background: colors.sidebar, display: "flex", flexDirection: "column", overflowY: "auto" }}>
        {/* Logo */}
        <div style={{ padding: "20px 18px 16px", borderBottom: "1px solid rgba(255,255,255,0.07)" }}>
          <div style={{ fontSize: 21, fontWeight: 800, color: "#fff", letterSpacing: "-0.5px" }}>
            R<span style={{ color: colors.green }}>3</span>VP
          </div>
          <div style={{ fontSize: 9, color: colors.green, textTransform: "uppercase", letterSpacing: "2px", marginTop: 2 }}>Demo Mode</div>
        </div>

        {/* Nav */}
        <div style={{ flex: 1, padding: "8px 0" }}>
          {NAV.map((section) => (
            <div key={section.section}>
              <div style={{ fontSize: 9, fontWeight: 700, textTransform: "uppercase", letterSpacing: "1.5px", color: "rgba(255,255,255,0.25)", padding: "12px 18px 4px" }}>
                {section.section}
              </div>
              {section.items.map((item) => (
                <button
                  key={item.key}
                  onClick={() => setActiveTab(item.key)}
                  style={{
                    display: "flex", alignItems: "center", gap: 8, padding: "7px 18px",
                    fontSize: 12, width: "100%", textAlign: "left", background: "none", border: "none",
                    cursor: "pointer", fontFamily: "inherit",
                    color: activeTab === item.key ? "#fff" : "rgba(255,255,255,0.55)",
                    borderLeft: activeTab === item.key ? `2px solid ${colors.green}` : "2px solid transparent",
                    backgroundColor: activeTab === item.key ? "rgba(0,179,54,0.12)" : "transparent",
                    fontWeight: activeTab === item.key ? 600 : 400,
                  }}
                >
                  <span style={{ fontSize: 13 }}>{item.icon}</span>
                  {item.label}
                </button>
              ))}
            </div>
          ))}
        </div>

        {/* User footer */}
        <div style={{ padding: "12px 18px", borderTop: "1px solid rgba(255,255,255,0.07)" }}>
          <div style={{ fontSize: 11, color: "rgba(255,255,255,0.45)", marginBottom: 6, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {user.email}
          </div>
          <button
            onClick={signOut}
            style={{ fontSize: 10, color: colors.green, background: "none", border: "none", cursor: "pointer", fontFamily: "inherit", padding: 0, fontWeight: 600 }}
          >
            Sign out
          </button>
        </div>
      </div>

      {/* Main */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        {/* Topbar */}
        <div style={{ flexShrink: 0, background: colors.surface, borderBottom: `1px solid ${colors.border}`, padding: "0 28px", height: 56, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div>
            <div style={{ fontSize: 16, fontWeight: 700, color: colors.text1 }}>{TAB_LABELS[activeTab]}</div>
            <div style={{ fontSize: 11, color: colors.text3, marginTop: 1 }}>Demo environment - sample data</div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: 11, color: colors.text3 }}>Signed in as</span>
            <span style={{ fontSize: 12, fontWeight: 600, color: colors.text1 }}>{user.displayName || user.email}</span>
            {user.photoURL && (
              <img src={user.photoURL} alt="" width={28} height={28} style={{ borderRadius: "50%", border: `2px solid ${colors.border}` }} />
            )}
          </div>
        </div>

        {/* Body */}
        <div style={{ flex: 1, overflowY: "auto", padding: "24px 28px", background: colors.bg }}>
          {/* Demo banner */}
          <div style={{ background: colors.blueBg, border: `1px solid #BFDBFE`, borderRadius: 8, padding: "8px 14px", marginBottom: 20, display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: colors.blue }}>
            <span style={{ fontWeight: 700 }}>Demo mode.</span>
            <span>All data is simulated. Connect a real appliance to see your actual recovery posture.</span>
          </div>

          {TAB_CONTENT[activeTab] ?? <PlaceholderTab label={TAB_LABELS[activeTab]} />}
        </div>
      </div>
    </div>
  );
}

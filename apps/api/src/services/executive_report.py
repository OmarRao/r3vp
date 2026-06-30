"""Executive report generation: CISO scorecard and digest email."""
from __future__ import annotations
import hashlib
import io
from datetime import datetime, timezone, timedelta
from typing import Any


def compute_scorecard(
    workloads_total: int,
    workloads_tested: int,
    workloads_passing: int,
    rto_compliance_pct: int,
    active_threats: int,
    open_incidents: int,
) -> int:
    """
    Compute overall readiness score 0-100.

    Formula:
      40% coverage (tested / total)
      35% pass rate (passing / tested, or 0 if none tested)
      15% RTO compliance
      10% threat penalty (capped at 10 points deducted)
    """
    coverage = (workloads_tested / workloads_total * 100) if workloads_total else 0
    pass_rate = (workloads_passing / workloads_tested * 100) if workloads_tested else 0
    threat_penalty = min(active_threats + open_incidents, 10)

    score = (
        coverage * 0.40
        + pass_rate * 0.35
        + rto_compliance_pct * 0.15
        - threat_penalty
    )
    return max(0, min(100, round(score)))


def render_scorecard_pdf(
    org_name: str,
    period_label: str,
    snapshot: dict[str, Any],
    trend: list[dict[str, Any]],
) -> bytes:
    """Render the CISO scorecard as a PDF via weasyprint."""
    from jinja2 import Environment, BaseLoader
    import weasyprint

    score = snapshot.get("overall_score", 0)
    score_color = "#00B336" if score >= 80 else "#D97706" if score >= 60 else "#DC2626"

    trend_rows = "".join(
        f"<tr><td>{t['date']}</td><td style='color:{('#00B336' if t['score'] >= 80 else '#D97706' if t['score'] >= 60 else '#DC2626')}'>{t['score']}</td><td>{t['passing']}/{t['total']}</td><td>{t['rto_pct']}%</td></tr>"
        for t in trend[-6:]
    )

    top_risks_rows = "".join(
        f"<tr><td>{r['workload']}</td><td><span style='color:{('#DC2626' if r['severity'] == 'high' else '#D97706')}'>{r['severity'].upper()}</span></td><td>{r['reason']}</td></tr>"
        for r in snapshot.get("top_risks", [])[:5]
    )

    provider_rows = "".join(
        f"<tr><td>{p}</td><td>{v.get('tested', 0)}/{v.get('total', 0)}</td><td>{v.get('pass_rate', 0)}%</td></tr>"
        for p, v in snapshot.get("provider_breakdown", {}).items()
    )

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @page {{ size: A4; margin: 20mm 18mm; }}
  body {{ font-family: -apple-system, 'Segoe UI', sans-serif; color: #0F172A; font-size: 11px; }}
  h1 {{ font-size: 20px; margin: 0 0 4px; }}
  .sub {{ color: #64748B; font-size: 12px; margin-bottom: 24px; }}
  .score-block {{ display: flex; align-items: center; gap: 24px; background: #F8FAFC; border-radius: 8px; padding: 16px 20px; margin-bottom: 20px; border-left: 4px solid {score_color}; }}
  .score-num {{ font-size: 48px; font-weight: 800; color: {score_color}; line-height: 1; }}
  .score-label {{ font-size: 13px; color: #475569; }}
  .kpi-row {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px; }}
  .kpi {{ background: #fff; border: 1px solid #E2E8F0; border-radius: 8px; padding: 12px 14px; }}
  .kpi-val {{ font-size: 22px; font-weight: 700; }}
  .kpi-lbl {{ font-size: 10px; color: #94A3B8; text-transform: uppercase; letter-spacing: .04em; margin-top: 2px; }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
  th {{ background: #F1F5F9; text-align: left; padding: 6px 10px; font-size: 9px; text-transform: uppercase; letter-spacing: .04em; color: #64748B; }}
  td {{ padding: 7px 10px; border-bottom: 1px solid #F1F5F9; font-size: 10px; }}
  h2 {{ font-size: 13px; font-weight: 700; margin: 18px 0 8px; border-bottom: 1px solid #E2E8F0; padding-bottom: 4px; }}
  .sig {{ margin-top: 24px; padding-top: 12px; border-top: 1px solid #E2E8F0; font-size: 9px; color: #94A3B8; }}
</style>
</head>
<body>
<h1>CISO Scorecard</h1>
<div class="sub">{org_name} &mdash; {period_label} &mdash; Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</div>

<div class="score-block">
  <div class="score-num">{score}</div>
  <div>
    <div style="font-size:15px;font-weight:700;">Overall Readiness Score</div>
    <div class="score-label">{snapshot.get('workloads_passing',0)} of {snapshot.get('workloads_total',0)} workloads passing &bull; {snapshot.get('rto_compliance_pct',0)}% RTO compliant</div>
  </div>
</div>

<div class="kpi-row">
  <div class="kpi"><div class="kpi-val">{snapshot.get('workloads_total',0)}</div><div class="kpi-lbl">Total Workloads</div></div>
  <div class="kpi"><div class="kpi-val">{snapshot.get('workloads_tested',0)}</div><div class="kpi-lbl">Tested</div></div>
  <div class="kpi"><div class="kpi-val" style="color:#DC2626">{snapshot.get('active_threats',0)}</div><div class="kpi-lbl">Active Threats</div></div>
  <div class="kpi"><div class="kpi-val" style="color:#D97706">{snapshot.get('open_incidents',0)}</div><div class="kpi-lbl">Open Incidents</div></div>
</div>

<h2>Score Trend</h2>
<table><thead><tr><th>Period</th><th>Score</th><th>Workloads</th><th>RTO Compliance</th></tr></thead>
<tbody>{trend_rows}</tbody></table>

<h2>Provider Breakdown</h2>
<table><thead><tr><th>Provider</th><th>Tested / Total</th><th>Pass Rate</th></tr></thead>
<tbody>{provider_rows}</tbody></table>

<h2>Top Risks</h2>
<table><thead><tr><th>Workload</th><th>Severity</th><th>Risk</th></tr></thead>
<tbody>{top_risks_rows or '<tr><td colspan="3" style="color:#94A3B8">No significant risks identified</td></tr>'}</tbody></table>

<div class="sig">R3VP Recovery Validation Platform &bull; Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy &bull; https://www.linkedin.com/in/omarrao/</div>
</body></html>"""

    pdf_bytes = weasyprint.HTML(string=html).write_pdf()
    return pdf_bytes


async def send_digest_email(
    recipients: list[str],
    subject: str,
    body_html: str,
    pdf_bytes: bytes,
    filename: str,
) -> None:
    """Send digest email with scorecard PDF attached."""
    import os
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.application import MIMEApplication

    smtp_host = os.getenv("SMTP_HOST", "localhost")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASS", "")
    from_addr = os.getenv("SMTP_FROM", "r3vp@example.com")

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(body_html, "html"))
    attachment = MIMEApplication(pdf_bytes, _subtype="pdf")
    attachment.add_header("Content-Disposition", "attachment", filename=filename)
    msg.attach(attachment)

    with smtplib.SMTP(smtp_host, smtp_port) as smtp:
        if smtp_user:
            smtp.starttls()
            smtp.login(smtp_user, smtp_pass)
        smtp.send_message(msg)

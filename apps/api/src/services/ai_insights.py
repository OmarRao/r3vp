"""AI-powered insights: RTO trend prediction, anomaly detection, natural language queries."""
# Author: Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
# https://www.linkedin.com/in/omarrao/
from __future__ import annotations

import statistics
from typing import Any


def predict_rto_trend(rto_readings: list[float], target_mins: float) -> dict[str, Any]:
    """
    Simple linear regression over RTO readings to predict breach risk.

    Returns: predicted next RTO, trend direction, risk level, projected breach date.
    """
    if len(rto_readings) < 2:
        return {"risk": "insufficient_data", "predicted_rto": None, "trend": "stable"}

    n = len(rto_readings)
    x = list(range(n))
    x_mean = sum(x) / n
    y_mean = sum(rto_readings) / n

    slope_num = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, rto_readings, strict=False))
    slope_den = sum((xi - x_mean) ** 2 for xi in x)
    slope = slope_num / slope_den if slope_den else 0
    intercept = y_mean - slope * x_mean

    predicted_next = intercept + slope * n
    predicted_next = max(0, round(predicted_next, 1))

    if slope > 0.5:
        trend = "degrading"
    elif slope < -0.5:
        trend = "improving"
    else:
        trend = "stable"

    risk = "low"
    breach_in_tests = None
    if predicted_next >= target_mins:
        risk = "critical"
    elif predicted_next >= target_mins * 0.85:
        risk = "high"
    elif predicted_next >= target_mins * 0.70:
        risk = "medium"

    if trend == "degrading" and predicted_next < target_mins and slope > 0:
        remaining = (target_mins - predicted_next) / slope
        breach_in_tests = max(0, round(remaining))

    return {
        "predicted_rto_mins": predicted_next,
        "trend": trend,
        "slope": round(slope, 3),
        "risk": risk,
        "breach_in_tests": breach_in_tests,
        "target_mins": target_mins,
        "current_rto_mins": round(rto_readings[-1], 1),
    }


def detect_anomalies(rto_series: list[float]) -> list[dict[str, Any]]:
    """
    Flag data points that are statistical anomalies (z-score > 2).
    Returns list of anomalous indices with z-scores.
    """
    if len(rto_series) < 4:
        return []
    mean = statistics.mean(rto_series)
    stdev = statistics.stdev(rto_series)
    if stdev == 0:
        return []
    anomalies = []
    for i, val in enumerate(rto_series):
        z = (val - mean) / stdev
        if abs(z) > 2.0:
            anomalies.append({"index": i, "value": round(val, 1), "z_score": round(z, 2), "direction": "spike" if z > 0 else "drop"})
    return anomalies


def rank_workload_risks(workloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Score and rank workloads by risk. Higher score = higher risk.

    Risk factors:
      - Days since last test (max 30 days = 30 pts)
      - RTO actual vs target ratio (if > 0.8 target, add up to 40 pts)
      - Recent failure rate (fail/total * 30 pts)
    """
    scored = []
    for wl in workloads:
        score = 0
        reasons = []

        days_stale = wl.get("days_since_test", 0)
        stale_pts = min(days_stale, 30)
        if stale_pts > 14:
            score += stale_pts
            reasons.append(f"Not tested in {days_stale} days")

        rto_actual = wl.get("rto_actual_mins", 0) or 0
        rto_target = wl.get("rto_target_mins", 999) or 999
        ratio = rto_actual / rto_target if rto_target else 0
        if ratio >= 0.8:
            rto_pts = min(round(ratio * 40), 40)
            score += rto_pts
            reasons.append(f"RTO at {round(ratio*100)}% of target ({rto_actual}m vs {rto_target}m)")

        fail_rate = wl.get("fail_rate_pct", 0) or 0
        if fail_rate > 0:
            fail_pts = round(fail_rate * 0.3)
            score += fail_pts
            if fail_rate > 20:
                reasons.append(f"Recent fail rate: {fail_rate}%")

        scored.append({
            "workload": wl.get("name"),
            "provider": wl.get("provider"),
            "risk_score": score,
            "risk_level": "high" if score >= 50 else "medium" if score >= 25 else "low",
            "reasons": reasons,
        })

    return sorted(scored, key=lambda x: x["risk_score"], reverse=True)


def answer_nl_query(query: str, context: dict[str, Any]) -> str:
    """
    Simple rule-based NL query handler over recovery test context.
    Matches common question patterns without an external LLM.
    """
    q = query.lower().strip()

    if any(k in q for k in ["how many workload", "total workload", "number of workload"]):
        total = context.get("workloads_total", 0)
        tested = context.get("workloads_tested", 0)
        return f"There are {total} workloads in total, of which {tested} have been tested."

    if "fail" in q and ("recent" in q or "last" in q or "this" in q):
        failures = context.get("recent_failures", [])
        if not failures:
            return "No failures recorded in the recent period."
        names = ", ".join(f["workload"] for f in failures[:5])
        return f"{len(failures)} workload(s) failed recently: {names}."

    if "rto" in q and ("breach" in q or "miss" in q or "exceed" in q):
        breaches = context.get("rto_breaches", [])
        if not breaches:
            return "No RTO breaches detected in the selected period."
        return f"{len(breaches)} workload(s) breached their RTO target. Highest offender: {breaches[0].get('workload')} at {breaches[0].get('rto_actual')} minutes against a {breaches[0].get('rto_target')} minute target."

    if "threat" in q or "malware" in q or "ransomware" in q:
        threats = context.get("active_threats", 0)
        return f"There are currently {threats} active threat finding(s) in the system."

    if "score" in q or "readiness" in q:
        score = context.get("overall_score", 0)
        return f"The current overall readiness score is {score}/100."

    if "provider" in q and ("worst" in q or "lowest" in q or "problem" in q):
        breakdown = context.get("provider_breakdown", {})
        if breakdown:
            worst = min(breakdown.items(), key=lambda x: x[1].get("pass_rate", 100))
            return f"The provider with the lowest pass rate is {worst[0]} at {worst[1].get('pass_rate', 0)}%."

    return "I can answer questions about workload counts, test failures, RTO breaches, threats, readiness scores, and provider performance. Try asking one of those."

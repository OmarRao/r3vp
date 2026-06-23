# Phase 11: AI Insights

**Status:** Complete

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/

---

## Overview

Phase 11 adds predictive analytics and natural language queries over R3VP test data. Three capabilities ship: RTO trend prediction using linear regression, statistical anomaly detection over recovery time series, and a rule-based natural language query interface for common recovery posture questions. No external LLM dependency is required.

---

## RTO Trend Prediction

Linear regression over historical RTO readings predicts the next test's expected RTO and flags breach risk before it occurs.

**Algorithm:**
1. Fit a least-squares line through the last N RTO readings
2. Project one step forward using `predicted = intercept + slope * n`
3. Compare prediction to the workload's RTO target to classify risk

**Risk levels:**

| Condition | Risk |
|---|---|
| Predicted RTO >= target | critical |
| Predicted RTO >= 85% of target | high |
| Predicted RTO >= 70% of target | medium |
| Below 70% of target | low |

**Trend direction:**
- slope > 0.5: degrading
- slope < -0.5: improving
- otherwise: stable

If the trend is degrading and the current RTO is below target, the service computes how many additional tests remain before a breach is projected.

---

## Anomaly Detection

Z-score analysis over the RTO time series flags individual test results that deviate significantly from the workload's historical baseline.

```
z = (value - mean) / stdev
```

Any reading with |z| > 2.0 is flagged as an anomaly. Direction is labeled as "spike" (z > 0) or "drop" (z < 0). Requires at least 4 readings to produce meaningful results.

---

## Workload Risk Ranking

All workloads are scored across three dimensions and ranked highest to lowest:

| Factor | Max Points | Condition |
|---|---|---|
| Test recency | 30 | Points = days_since_test if > 14 days, capped at 30 |
| RTO proximity | 40 | Points = min(ratio * 40, 40) if ratio >= 0.80 |
| Failure rate | 30 | Points = fail_rate * 0.3 |

Risk levels: high (>= 50), medium (>= 25), low (< 25).

---

## Natural Language Query

A rule-based query handler answers common recovery posture questions without an external LLM. Matched patterns:

| Query pattern | Example answer |
|---|---|
| "how many workloads" | Total count and tested count |
| "fail" + "recent/last/this" | List of recently failing workloads |
| "rto" + "breach/miss/exceed" | Count and worst offender with times |
| "threat/malware/ransomware" | Active threat count |
| "score/readiness" | Current overall score |
| "provider" + "worst/lowest/problem" | Lowest pass rate provider |

Unmatched queries receive a prompt listing supported question types.

---

## API Endpoints

No new database tables are required. All endpoints read from existing `test_runs`, `workloads`, and `scorecard_snapshots` tables.

| Method | Path | Permission | Description |
|---|---|---|---|
| GET | `/api/v1/insights/rto-prediction/{workload_id}` | workloads:read | Trend prediction + anomalies for one workload |
| GET | `/api/v1/insights/risk-ranking` | workloads:read | All workloads ranked by risk score |
| POST | `/api/v1/insights/query` | workloads:read | Natural language query (body: `{"query": "..."}`) |

---

## Example: RTO Prediction Response

```json
{
  "workload_id": "db-prod-03",
  "rto_series": [28.0, 31.0, 35.0, 38.0, 44.0, 52.0],
  "prediction": {
    "predicted_rto_mins": 58.1,
    "trend": "degrading",
    "slope": 4.743,
    "risk": "high",
    "breach_in_tests": 2,
    "target_mins": 60.0,
    "current_rto_mins": 52.0
  },
  "anomalies": []
}
```

---

*Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy*
*https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/*

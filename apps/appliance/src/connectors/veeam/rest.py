# Copyright (c) 2026 Omar Rao
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Commercial
# This file is available under the GNU Affero General Public License v3.0
# or under a separate commercial license.

"""Pure request-building and response-parsing helpers for the Veeam B&R REST API.

Everything in this module is a pure function: no network, no config, no I/O. The
async ``VeeamClient`` composes these to talk to a live server, and the unit tests
exercise them directly against recorded fixture JSON (see ``tests/fixtures/veeam``).
Keeping the wire logic pure is what lets version detection, restore-point
selection, instant-recovery request shaping, and session-state polling be tested
offline, with no Veeam server present.

Supports Veeam 11 (v1.0), Veeam 12 (v1.1), and Veeam 13.0.2+ (v1.2).

Built by Omar Rao, Engineer - Data Resilience, Cybersecurity and Privacy
https://www.linkedin.com/in/omarrao/ | https://omarrao.substack.com/
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from .models import VeeamRestorePoint
from .session_states import is_recovery_published, is_terminal_failure

DEFAULT_RECOVERY_REASON = "R3VP automated recovery validation"


# -- Version detection ---------------------------------------------------------

# Conservative x-api-version used before the server build is known (the token
# and serverInfo calls). Broadly supported by Veeam 12.1 and later; the header
# is upgraded to the exact matching version once serverInfo reports the build.
DEFAULT_X_API_VERSION = "1.1-rev1"


def build_version_tuple(build_version: str | None) -> tuple[int, int, int, int]:
    """Parse a Veeam build like '13.1.0.1234' into (major, minor, patch, build).

    Missing or unparseable components default to 0, so a partial or garbage
    build string never raises.
    """
    parts = (build_version or "").split(".")
    out: list[int] = []
    for i in range(4):
        try:
            out.append(int(parts[i].strip()))
        except (IndexError, ValueError):
            out.append(0)
    return out[0], out[1], out[2], out[3]


def api_version_for_build(build_version: str | None) -> str:
    """Internal capability tier used to pick endpoint shapes (not the wire
    version). Returns 'v1.2' for Veeam 13.x (newest known shapes), 'v1.1' for
    Veeam 12.x, else 'v1.0'. The real REST version sent on the wire is
    `x_api_version`. A missing/unparseable build falls back to 'v1.0'.
    """
    major = build_version_tuple(build_version)[0]
    if major >= 13:
        return "v1.2"
    if major == 12:
        return "v1.1"
    return "v1.0"


def x_api_version(build_version: str | None) -> str:
    """Return the Veeam `x-api-version` header value for a product build.

    Veeam requires this header (format `<version>-<revision>`, e.g. '1.3-rev1')
    on every REST request. The value is derived from the server's reported
    buildVersion so it always matches the target server. Mapping is grounded in
    the Veeam Help Center version ladder:
      - 13.0.1+ (including 13.1) -> 1.3-rev1;  13.0.0 -> 1.3-rev0
      - 12.3.1+ -> 1.2-rev1;  12.2.x -> 1.2-rev0;  12.1.x -> 1.1-rev1;  12.0.x -> 1.1-rev0
      - 11.x -> 1.0-rev1
    NOTE: the exact 13.1 revision should be confirmed against a live 13.1
    server; 1.3-rev1 is the correct floor for 13.0.1 and later. Unknown or
    unparseable builds fall back to DEFAULT_X_API_VERSION.
    """
    if not build_version:
        return DEFAULT_X_API_VERSION
    major, minor, patch, build = build_version_tuple(build_version)
    if major >= 13:
        return "1.3-rev0" if (major, minor, patch, build) < (13, 0, 1, 0) else "1.3-rev1"
    if major == 12:
        if (minor, patch) >= (3, 1):
            return "1.2-rev1"
        if minor >= 2:
            return "1.2-rev0"
        if minor >= 1:
            return "1.1-rev1"
        return "1.1-rev0"
    if major == 11:
        return "1.0-rev1"
    return DEFAULT_X_API_VERSION


def parse_server_info(body: dict) -> dict:
    """Extract build version / id / name from a serverInfo response body."""
    build_version = body.get("buildVersion")
    return {
        "build_version": build_version,
        "vbr_id": body.get("vbrId"),
        "server_name": body.get("name"),
        "api_version": api_version_for_build(build_version),
        "rest_api_version": x_api_version(build_version),
    }


# -- Auth ----------------------------------------------------------------------

@dataclass(frozen=True)
class TokenInfo:
    access_token: str
    expires_in: int


def build_token_request(username: str, password: str) -> dict:
    """Return the form body for the OAuth2 password-grant token request."""
    return {
        "grant_type": "password",
        "username": username,
        "password": password,
    }


def parse_token_response(body: dict) -> TokenInfo:
    """Parse the token endpoint response. Defaults expiry to 900s if omitted."""
    return TokenInfo(
        access_token=body["access_token"],
        expires_in=int(body.get("expires_in", 900)),
    )


# -- Restore-point discovery ---------------------------------------------------

def restore_points_path(api_version: str, object_id: str) -> tuple[str, dict]:
    """Return the (path, query-params) for listing restore points of an object.

    Veeam 12 (v1.1) and 13 (v1.2): GET /backupObjects/{id}/restorePoints
    Veeam 11 (v1.0):               GET /restorePoints?backupObjectId={id}
    """
    if api_version in ("v1.1", "v1.2"):
        return f"/backupObjects/{object_id}/restorePoints", {}
    return "/restorePoints", {"backupObjectId": object_id}


def parse_restore_points(body: dict) -> list[VeeamRestorePoint]:
    """Parse a restore-points list response into models."""
    return [VeeamRestorePoint.model_validate(r) for r in body.get("data", [])]


class NoRestorePointError(RuntimeError):
    """Raised when no usable restore point can be selected."""


def select_restore_point(
    points: list[VeeamRestorePoint],
    now: datetime,
    rpo_target_mins: int | None = None,
) -> VeeamRestorePoint:
    """Select the newest consistent restore point.

    When ``rpo_target_mins`` is given and at least one consistent point falls
    inside that window, the newest in-window point is returned. Otherwise the
    newest consistent point overall is returned (the caller still measures the
    real RPO and can fail the run on the target). Raises ``NoRestorePointError``
    when there is nothing consistent to recover from.
    """
    if not points:
        raise NoRestorePointError("no restore points returned by Veeam")
    consistent = [p for p in points if p.is_consistent]
    if not consistent:
        raise NoRestorePointError("no consistent restore points available")
    consistent.sort(key=lambda p: p.creationTime, reverse=True)
    if rpo_target_mins is not None:
        in_window = [
            p for p in consistent
            if compute_age_minutes(p.creationTime, now) <= rpo_target_mins
        ]
        if in_window:
            return in_window[0]
    return consistent[0]


# -- Instant recovery ----------------------------------------------------------

def instant_recovery_endpoint(api_version: str) -> str:
    """Return the version-correct instant-recovery start endpoint.

    Veeam 13 (v1.2) exposes /restore/instantRecovery/vmware/vm; earlier versions
    use /instantRecovery/vmware/vm. v1.0 does not support the REST-driven
    instant-recovery flow.
    """
    if api_version == "v1.0":
        raise NotImplementedError("instant recovery REST API requires Veeam 11+ (v1.1)")
    if api_version == "v1.2":
        return "/restore/instantRecovery/vmware/vm"
    return "/instantRecovery/vmware/vm"


def build_instant_recovery_request(
    api_version: str,
    restore_point_id: str,
    isolated_network: str,
    target_datastore: str = "",
    reason: str = DEFAULT_RECOVERY_REASON,
) -> tuple[str, dict]:
    """Build the (endpoint, body) for starting instant recovery into isolation.

    Every NIC is remapped to the isolated portgroup ("*" source matches any
    source network) so the recovered guest cannot reach production.
    """
    endpoint = instant_recovery_endpoint(api_version)
    body: dict = {
        "restorePointId": restore_point_id,
        "networkMapping": [
            {"sourceNetwork": "*", "targetNetwork": isolated_network}
        ],
        "powerOn": True,
        "reason": reason,
    }
    if target_datastore:
        body["targetDatastoreId"] = target_datastore
    return endpoint, body


def parse_session_id(body: dict) -> str:
    """Extract the session id from a start-recovery response.

    Different Veeam versions key this as 'sessionId' or 'id'.
    """
    session_id = body.get("sessionId") or body.get("id")
    if not session_id:
        raise KeyError("no sessionId/id in instant-recovery response")
    return str(session_id)


def stop_publishing_path(api_version: str, session_id: str) -> str:
    """Return the teardown (stop-publishing) path for an instant-recovery mount."""
    if api_version == "v1.2":
        return f"/restore/instantRecovery/vmware/vm/{session_id}/stopPublishing"
    return f"/instantRecovery/vmware/vm/{session_id}/stopPublishing"


# -- Session-state polling -----------------------------------------------------

def parse_session_state(body: dict) -> str:
    """Return the session ``state`` string, or 'unknown' when absent."""
    return body.get("state", "unknown")


class PollDecision(str, Enum):
    PUBLISHED = "published"   # mount published, VM available -> proceed
    FAILED = "failed"         # terminal failure -> abort
    WAIT = "wait"             # transient -> keep polling


def classify_poll(state: str) -> PollDecision:
    """Classify one polled session state into a polling decision."""
    if is_recovery_published(state):
        return PollDecision.PUBLISHED
    if is_terminal_failure(state):
        return PollDecision.FAILED
    return PollDecision.WAIT


# -- RTO / RPO measurement -----------------------------------------------------

def compute_age_minutes(then: datetime, now: datetime) -> int:
    """Whole minutes between two aware timestamps (floored, never negative)."""
    delta = now - then
    return max(0, int(delta.total_seconds() // 60))


def compute_rpo_minutes(restore_point_creation: datetime, now: datetime) -> int:
    """RPO = age of the recovered restore point at validation time, in minutes."""
    return compute_age_minutes(restore_point_creation, now)


def compute_rto_minutes(recovery_start: datetime, boot_ready: datetime) -> int:
    """RTO = time from starting recovery to the guest being boot-ready, minutes."""
    return compute_age_minutes(recovery_start, boot_ready)


def readiness_score(
    health_passed: bool,
    rto_actual_mins: int,
    rto_target_mins: int,
    rpo_actual_mins: int,
    rpo_target_mins: int,
) -> int:
    """Compute a 0-100 recovery-readiness score.

    Health is the dominant signal (60 points). RTO and RPO each contribute up to
    20 points, scaled down when the measured value exceeds its target. The score
    is clamped to [0, 100].
    """
    score = 60 if health_passed else 0
    score += _objective_points(rto_actual_mins, rto_target_mins, 20)
    score += _objective_points(rpo_actual_mins, rpo_target_mins, 20)
    return max(0, min(100, score))


def _objective_points(actual: int, target: int, max_points: int) -> int:
    if target <= 0:
        return max_points if actual <= 0 else 0
    if actual <= target:
        return max_points
    # Linear decay: at 2x target -> 0 points.
    overshoot = (actual - target) / target
    return max(0, int(round(max_points * (1 - overshoot))))

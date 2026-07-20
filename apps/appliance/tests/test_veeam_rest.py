"""Fixture-driven unit tests for the pure Veeam REST logic.

These exercise version detection, auth request/response shaping, restore-point
discovery + selection, instant-recovery request building, session-state polling
classification, and RTO/RPO/readiness measurement -- all against recorded JSON
under tests/fixtures/veeam, with no Veeam server and no native deps (no yara,
no pyVmomi). They run in the "Appliance - lint & test" CI job.

Built by Omar Rao.
"""
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.connectors.veeam import rest
from src.connectors.veeam.rest import NoRestorePointError, PollDecision

FIXTURES = Path(__file__).parent / "fixtures" / "veeam"


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


# -- version detection ---------------------------------------------------------

@pytest.mark.parametrize(
    "build, expected",
    [
        ("13.0.2.1234", "v1.2"),
        ("12.1.0.2131", "v1.1"),
        ("11.0.1.1261", "v1.0"),
        ("10.0.0.4461", "v1.0"),
        (None, "v1.0"),
        ("", "v1.0"),
        ("garbage", "v1.0"),
    ],
)
def test_api_version_for_build(build, expected):
    assert rest.api_version_for_build(build) == expected


def test_parse_server_info_v13():
    info = rest.parse_server_info(load("server_info_v13.json"))
    assert info["api_version"] == "v1.2"
    assert info["build_version"] == "13.0.2.1234"
    assert info["server_name"] == "vbr-lab-01.corp.local"
    assert info["vbr_id"]


def test_parse_server_info_v12():
    info = rest.parse_server_info(load("server_info_v12.json"))
    assert info["api_version"] == "v1.1"


def test_parse_server_info_missing_build_defaults_conservative():
    info = rest.parse_server_info({})
    assert info["api_version"] == "v1.0"
    assert info["build_version"] is None


# -- auth ----------------------------------------------------------------------

def test_build_token_request():
    body = rest.build_token_request("svc-r3vp", "s3cret")
    assert body == {
        "grant_type": "password",
        "username": "svc-r3vp",
        "password": "s3cret",
    }


def test_parse_token_response():
    tok = rest.parse_token_response(load("token.json"))
    assert tok.access_token.startswith("eyJ")
    assert tok.expires_in == 900


def test_parse_token_response_defaults_expiry():
    tok = rest.parse_token_response({"access_token": "x"})
    assert tok.expires_in == 900


# -- restore-point discovery + selection --------------------------------------

@pytest.mark.parametrize(
    "version, expected_path, expected_params",
    [
        ("v1.2", "/backupObjects/vm-1/restorePoints", {}),
        ("v1.1", "/backupObjects/vm-1/restorePoints", {}),
        ("v1.0", "/restorePoints", {"backupObjectId": "vm-1"}),
    ],
)
def test_restore_points_path(version, expected_path, expected_params):
    path, params = rest.restore_points_path(version, "vm-1")
    assert path == expected_path
    assert params == expected_params


def test_parse_and_select_restore_point_picks_newest_consistent():
    points = rest.parse_restore_points(load("restore_points.json"))
    assert len(points) == 3
    # now = 09:45; 09:30 point is newer but crash-consistent -> skipped.
    now = datetime(2026, 7, 20, 9, 45, tzinfo=UTC)
    best = rest.select_restore_point(points, now)
    assert best.id == "rp-2026-07-20T09-00"
    assert best.is_consistent


def test_select_restore_point_prefers_in_window():
    points = rest.parse_restore_points(load("restore_points.json"))
    now = datetime(2026, 7, 20, 9, 45, tzinfo=UTC)
    # 60-min RPO window -> 09:00 (45 min old) qualifies; the 06:00 does not.
    best = rest.select_restore_point(points, now, rpo_target_mins=60)
    assert best.id == "rp-2026-07-20T09-00"


def test_select_restore_point_falls_back_when_none_in_window():
    points = rest.parse_restore_points(load("restore_points.json"))
    now = datetime(2026, 7, 20, 9, 45, tzinfo=UTC)
    # 5-min window: nothing consistent is that fresh -> newest consistent overall.
    best = rest.select_restore_point(points, now, rpo_target_mins=5)
    assert best.id == "rp-2026-07-20T09-00"


def test_select_restore_point_no_points():
    with pytest.raises(NoRestorePointError):
        rest.select_restore_point([], datetime.now(UTC))


def test_select_restore_point_no_consistent():
    points = rest.parse_restore_points(
        {"data": [{"id": "x", "creationTime": "2026-07-20T09:30:00+00:00",
                   "isConsistent": False}]}
    )
    with pytest.raises(NoRestorePointError):
        rest.select_restore_point(points, datetime.now(UTC))


# -- instant recovery ----------------------------------------------------------

@pytest.mark.parametrize(
    "version, endpoint",
    [
        ("v1.2", "/restore/instantRecovery/vmware/vm"),
        ("v1.1", "/instantRecovery/vmware/vm"),
    ],
)
def test_instant_recovery_endpoint(version, endpoint):
    assert rest.instant_recovery_endpoint(version) == endpoint


def test_instant_recovery_endpoint_v10_unsupported():
    with pytest.raises(NotImplementedError):
        rest.instant_recovery_endpoint("v1.0")


def test_build_instant_recovery_request_isolates_all_nics():
    endpoint, body = rest.build_instant_recovery_request(
        "v1.2", "rp-1", "r3vp-isolated-abc123"
    )
    assert endpoint == "/restore/instantRecovery/vmware/vm"
    assert body["restorePointId"] == "rp-1"
    assert body["powerOn"] is True
    assert body["networkMapping"] == [
        {"sourceNetwork": "*", "targetNetwork": "r3vp-isolated-abc123"}
    ]
    # No datastore key when none supplied (Veeam auto-resolves).
    assert "targetDatastoreId" not in body


def test_build_instant_recovery_request_with_datastore():
    _, body = rest.build_instant_recovery_request(
        "v1.1", "rp-1", "isolated", target_datastore="ds-42"
    )
    assert body["targetDatastoreId"] == "ds-42"


def test_parse_session_id_sessionid_key():
    assert rest.parse_session_id(load("instant_recovery_response.json")) == "sess-ir-7f3a12"


def test_parse_session_id_id_key():
    assert rest.parse_session_id({"id": "sess-9"}) == "sess-9"


def test_parse_session_id_missing():
    with pytest.raises(KeyError):
        rest.parse_session_id({"name": "no-id"})


@pytest.mark.parametrize(
    "version, expected",
    [
        ("v1.2", "/restore/instantRecovery/vmware/vm/sess-1/stopPublishing"),
        ("v1.1", "/instantRecovery/vmware/vm/sess-1/stopPublishing"),
    ],
)
def test_stop_publishing_path(version, expected):
    assert rest.stop_publishing_path(version, "sess-1") == expected


# -- session-state polling -----------------------------------------------------

def test_parse_session_state_present():
    assert rest.parse_session_state(load("session_working.json")) == "Working"


def test_parse_session_state_absent():
    assert rest.parse_session_state(load("session_no_state.json")) == "unknown"


@pytest.mark.parametrize(
    "fixture, decision",
    [
        ("session_working.json", PollDecision.PUBLISHED),
        ("session_failed.json", PollDecision.FAILED),
        ("session_starting.json", PollDecision.WAIT),
        ("session_no_state.json", PollDecision.WAIT),
    ],
)
def test_classify_poll_transitions(fixture, decision):
    state = rest.parse_session_state(load(fixture))
    assert rest.classify_poll(state) == decision


def test_full_poll_sequence_starting_then_working():
    # Simulate a polling loop over recorded state transitions.
    sequence = ["session_starting.json", "session_starting.json", "session_working.json"]
    decisions = [rest.classify_poll(rest.parse_session_state(load(f))) for f in sequence]
    assert decisions[:-1] == [PollDecision.WAIT, PollDecision.WAIT]
    assert decisions[-1] == PollDecision.PUBLISHED


def test_full_poll_sequence_ends_failed():
    sequence = ["session_starting.json", "session_failed.json"]
    decisions = [rest.classify_poll(rest.parse_session_state(load(f))) for f in sequence]
    assert decisions == [PollDecision.WAIT, PollDecision.FAILED]


# -- RTO / RPO / readiness -----------------------------------------------------

def test_compute_rpo_minutes():
    created = datetime(2026, 7, 20, 9, 0, tzinfo=UTC)
    now = datetime(2026, 7, 20, 9, 45, tzinfo=UTC)
    assert rest.compute_rpo_minutes(created, now) == 45


def test_compute_rto_minutes():
    start = datetime(2026, 7, 20, 10, 0, tzinfo=UTC)
    ready = datetime(2026, 7, 20, 10, 8, 30, tzinfo=UTC)
    assert rest.compute_rto_minutes(start, ready) == 8


def test_compute_age_never_negative():
    now = datetime(2026, 7, 20, 9, 0, tzinfo=UTC)
    future = datetime(2026, 7, 20, 9, 30, tzinfo=UTC)
    assert rest.compute_age_minutes(future, now) == 0


def test_readiness_score_all_within_target():
    assert rest.readiness_score(True, 5, 15, 30, 60) == 100


def test_readiness_score_health_fail_dominates():
    # Health failed removes the 60-point block even when RTO/RPO are perfect.
    assert rest.readiness_score(False, 5, 15, 30, 60) == 40


def test_readiness_score_rto_overshoot_decays():
    # RTO at 2x target -> 0 of its 20 points; RPO fine -> 60 + 0 + 20 = 80.
    assert rest.readiness_score(True, 30, 15, 30, 60) == 80


def test_readiness_score_clamped():
    score = rest.readiness_score(False, 999, 15, 999, 60)
    assert 0 <= score <= 100
    assert score == 0

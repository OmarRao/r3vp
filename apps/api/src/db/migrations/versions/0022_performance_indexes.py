"""Performance indexes on hot filter/join columns

Adds btree indexes on the foreign-key, org_id, status, and timestamp columns
that the dashboard, readiness, scorecard, MSSP, and threat endpoints filter and
join on. Postgres does not auto-index foreign-key columns, so these were
sequential scans. Index names match the `index=True` declarations on the ORM
models so `create_all` (tests) and the migrated schema agree.

Revision ID: 0022
Revises: 0021
"""
from alembic import op

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None

# (index_name, table, column)
INDEXES = [
    ("ix_test_runs_workload_id", "test_runs", "workload_id"),
    ("ix_test_runs_started_at", "test_runs", "started_at"),
    ("ix_test_runs_completed_at", "test_runs", "completed_at"),
    ("ix_test_runs_status", "test_runs", "status"),
    ("ix_test_run_steps_run_id", "test_run_steps", "run_id"),
    ("ix_health_check_results_run_id", "health_check_results", "run_id"),
    ("ix_users_org_id", "users", "org_id"),
    ("ix_appliances_org_id", "appliances", "org_id"),
    ("ix_workloads_appliance_id", "workloads", "appliance_id"),
    ("ix_integrations_org_id", "integrations", "org_id"),
    ("ix_threat_scans_org_id", "threat_scans", "org_id"),
    ("ix_threat_findings_org_id", "threat_findings", "org_id"),
    ("ix_threat_incidents_org_id", "threat_incidents", "org_id"),
    ("ix_mssp_customer_orgs_mssp_id", "mssp_customer_orgs", "mssp_id"),
    ("ix_mssp_alert_rules_mssp_id", "mssp_alert_rules", "mssp_id"),
    ("ix_org_members_org_id", "org_members", "org_id"),
    ("ix_org_invites_org_id", "org_invites", "org_id"),
    ("ix_api_keys_org_id", "api_keys", "org_id"),
    ("ix_notification_channels_org_id", "notification_channels", "org_id"),
]


def upgrade() -> None:
    for name, table, column in INDEXES:
        op.execute(f'CREATE INDEX IF NOT EXISTS {name} ON {table} ("{column}")')


def downgrade() -> None:
    for name, _table, _column in INDEXES:
        op.execute(f"DROP INDEX IF EXISTS {name}")

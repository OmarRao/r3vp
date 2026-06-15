"""Add threat_scans, threat_findings, threat_incidents tables.

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "threat_scans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("appliance_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("appliances.id"), nullable=False),
        sa.Column("scan_id", sa.String(255), unique=True, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("hosts_scanned", sa.Integer, server_default="1"),
        sa.Column("signatures_checked", sa.Integer, server_default="0"),
        sa.Column("yara_rules_checked", sa.Integer, server_default="0"),
        sa.Column("critical_count", sa.Integer, server_default="0"),
        sa.Column("high_count", sa.Integer, server_default="0"),
        sa.Column("medium_count", sa.Integer, server_default="0"),
        sa.Column("low_count", sa.Integer, server_default="0"),
        sa.Column("error", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_threat_scans_org_id", "threat_scans", ["org_id"])
    op.create_index("ix_threat_scans_appliance_id", "threat_scans", ["appliance_id"])

    op.create_table(
        "threat_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("threat_scans.id"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("signature_id", sa.String(255), nullable=False),
        sa.Column("threat_name", sa.String(255), nullable=False),
        sa.Column("threat_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(50), nullable=False),
        sa.Column("host", sa.String(255), nullable=False),
        sa.Column("indicator_type", sa.String(50), nullable=False),
        sa.Column("indicator_value", sa.String(1024), nullable=False),
        sa.Column("context", postgresql.JSONB, server_default="{}"),
        sa.Column("mitre_technique", sa.String(50)),
        sa.Column("status", sa.String(50), server_default="'active'"),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_threat_findings_org_id", "threat_findings", ["org_id"])
    op.create_index("ix_threat_findings_severity", "threat_findings", ["severity"])
    op.create_index("ix_threat_findings_status", "threat_findings", ["status"])

    op.create_table(
        "threat_incidents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("incident_number", sa.String(50), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("severity", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), server_default="'active'"),
        sa.Column("affected_host", sa.String(255), nullable=False),
        sa.Column("threat_name", sa.String(255), nullable=False),
        sa.Column("finding_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("threat_findings.id")),
        sa.Column("backup_triggered", sa.Boolean, server_default="false"),
        sa.Column("backup_job_id", sa.String(255)),
        sa.Column("soar_dispatched", sa.Boolean, server_default="false"),
        sa.Column("soar_incident_id", sa.String(255)),
        sa.Column("siem_dispatched", sa.Boolean, server_default="false"),
        sa.Column("veeamone_reported", sa.Boolean, server_default="false"),
        sa.Column("notifications_sent", sa.Boolean, server_default="false"),
        sa.Column("ir_log", postgresql.JSONB, server_default="'[]'"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_threat_incidents_org_id", "threat_incidents", ["org_id"])
    op.create_index("ix_threat_incidents_status", "threat_incidents", ["status"])


def downgrade() -> None:
    op.drop_table("threat_incidents")
    op.drop_table("threat_findings")
    op.drop_table("threat_scans")

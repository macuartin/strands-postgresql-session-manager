"""Use JSONB and add multi-agent repository state."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260910_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("agents", "state", type_=postgresql.JSONB(), postgresql_using="state::jsonb")
    op.alter_column(
        "agents",
        "conversation_manager_state",
        type_=postgresql.JSONB(),
        postgresql_using="conversation_manager_state::jsonb",
    )
    op.alter_column(
        "agents",
        "_internal_state",
        type_=postgresql.JSONB(),
        postgresql_using="_internal_state::jsonb",
    )
    op.alter_column(
        "messages", "message", type_=postgresql.JSONB(), postgresql_using="message::jsonb"
    )
    op.alter_column(
        "messages",
        "redact_message",
        type_=postgresql.JSONB(),
        postgresql_using="redact_message::jsonb",
    )
    op.create_table(
        "multi_agents",
        sa.Column("session_id", sa.String(length=255), nullable=False),
        sa.Column("multi_agent_id", sa.String(length=255), nullable=False),
        sa.Column("state", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.session_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("session_id", "multi_agent_id"),
    )
    op.create_foreign_key(
        "fk_messages_agent",
        "messages",
        "agents",
        ["session_id", "agent_id"],
        ["session_id", "agent_id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint("fk_messages_agent", "messages", type_="foreignkey")
    op.drop_table("multi_agents")
    op.alter_column(
        "messages", "redact_message", type_=sa.JSON(), postgresql_using="redact_message::json"
    )
    op.alter_column("messages", "message", type_=sa.JSON(), postgresql_using="message::json")
    op.alter_column(
        "agents", "_internal_state", type_=sa.JSON(), postgresql_using="_internal_state::json"
    )
    op.alter_column(
        "agents",
        "conversation_manager_state",
        type_=sa.JSON(),
        postgresql_using="conversation_manager_state::json",
    )
    op.alter_column("agents", "state", type_=sa.JSON(), postgresql_using="state::json")

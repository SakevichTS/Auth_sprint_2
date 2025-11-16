"""create partition

Revision ID: 9142f999b10c
Revises: 07e2dbbc959e
Create Date: 2025-11-16 14:42:46.360972

"""
from datetime import datetime, timedelta
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9142f999b10c'
down_revision: Union[str, Sequence[str], None] = '07e2dbbc959e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.drop_index('ix_login_audit_user_ts', table_name='login_audit')
    op.drop_table('login_audit')

    op.execute("""
        CREATE TABLE login_audit (
            id UUID PRIMARY KEY,
            user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            ts TIMESTAMPTZ NOT NULL,
            ip_address VARCHAR(64),
            user_agent VARCHAR(255),
            result login_result NOT NULL,
            reason VARCHAR(255)
        ) PARTITION BY RANGE (ts);
    """)

    op.create_index('ix_login_audit_user_ts', 'login_audit', ['user_id', 'ts'], unique=False)

    op.execute("""
        CREATE TABLE login_audit_2025_01
            PARTITION OF login_audit
            FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');
    """)


def downgrade():
    op.drop_table('login_audit')

    op.create_table('login_audit',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=True),
    sa.Column('ts', sa.DateTime(timezone=True), nullable=False),
    sa.Column('ip_address', sa.String(length=64), nullable=True),
    sa.Column('user_agent', sa.String(length=255), nullable=True),
    sa.Column('result', sa.Enum('success', 'fail', name='login_result'), nullable=False),
    sa.Column('reason', sa.String(length=255), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_login_audit_user_ts', 'login_audit', ['user_id', 'ts'], unique=False)

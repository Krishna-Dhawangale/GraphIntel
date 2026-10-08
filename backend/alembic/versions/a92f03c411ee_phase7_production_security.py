"""phase7_production_security

Revision ID: a92f03c411ee
Revises: 8b8b5e19accc
Create Date: 2026-10-05 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a92f03c411ee'
down_revision: Union[str, None] = '8b8b5e19accc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update users table
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('role', sa.String(length=50), nullable=False, server_default='USER'))
        batch_op.add_column(sa.Column('tenant_id', sa.String(length=64), nullable=False, server_default='default_tenant'))
        batch_op.create_index('ix_users_role', ['role'])
        batch_op.create_index('ix_users_tenant_id', ['tenant_id'])

    # 2. Update documents table
    with op.batch_alter_table('documents') as batch_op:
        batch_op.add_column(sa.Column('tenant_id', sa.String(length=64), nullable=False, server_default='default_tenant'))
        batch_op.add_column(sa.Column('content_hash', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.create_index('ix_documents_tenant_id', ['tenant_id'])
        batch_op.create_index('ix_documents_content_hash', ['content_hash'])
        batch_op.create_index('ix_documents_is_deleted', ['is_deleted'])

    # 3. Update document_chunks table
    with op.batch_alter_table('document_chunks') as batch_op:
        batch_op.add_column(sa.Column('tenant_id', sa.String(length=64), nullable=True))
        batch_op.create_index('ix_document_chunks_tenant_id', ['tenant_id'])

    # 4. Update queries table
    with op.batch_alter_table('queries') as batch_op:
        batch_op.add_column(sa.Column('tenant_id', sa.String(length=64), nullable=True))
        batch_op.create_index('ix_queries_tenant_id', ['tenant_id'])

    # 5. Update ingestion_jobs table
    with op.batch_alter_table('ingestion_jobs') as batch_op:
        batch_op.add_column(sa.Column('tenant_id', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'))
        batch_op.create_index('ix_ingestion_jobs_tenant_id', ['tenant_id'])

    # 6. Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('tenant_id', sa.String(length=64), nullable=True),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('resource_type', sa.String(length=64), nullable=True),
        sa.Column('resource_id', sa.String(length=64), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='SUCCESS'),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=255), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    with op.batch_alter_table('audit_logs') as batch_op:
        batch_op.create_index('ix_audit_logs_user_id', ['user_id'])
        batch_op.create_index('ix_audit_logs_tenant_id', ['tenant_id'])
        batch_op.create_index('ix_audit_logs_action', ['action'])
        batch_op.create_index('ix_audit_logs_resource_type', ['resource_type'])
        batch_op.create_index('ix_audit_logs_resource_id', ['resource_id'])
        batch_op.create_index('ix_audit_logs_status', ['status'])


def downgrade() -> None:
    op.drop_table('audit_logs')

    with op.batch_alter_table('ingestion_jobs') as batch_op:
        batch_op.drop_index('ix_ingestion_jobs_tenant_id')
        batch_op.drop_column('retry_count')
        batch_op.drop_column('tenant_id')

    with op.batch_alter_table('queries') as batch_op:
        batch_op.drop_index('ix_queries_tenant_id')
        batch_op.drop_column('tenant_id')

    with op.batch_alter_table('document_chunks') as batch_op:
        batch_op.drop_index('ix_document_chunks_tenant_id')
        batch_op.drop_column('tenant_id')

    with op.batch_alter_table('documents') as batch_op:
        batch_op.drop_index('ix_documents_is_deleted')
        batch_op.drop_index('ix_documents_content_hash')
        batch_op.drop_index('ix_documents_tenant_id')
        batch_op.drop_column('deleted_at')
        batch_op.drop_column('is_deleted')
        batch_op.drop_column('content_hash')
        batch_op.drop_column('tenant_id')

    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_index('ix_users_tenant_id')
        batch_op.drop_index('ix_users_role')
        batch_op.drop_column('tenant_id')
        batch_op.drop_column('role')

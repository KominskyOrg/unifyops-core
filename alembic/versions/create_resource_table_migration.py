"""Create resources table

Revision ID: 0003
Create Date: 2025-04-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers
revision = '0003'
down_revision = '0002'  # Reference the existing migration
branch_labels = None
depends_on = None


def upgrade():
    # Create resources table
    op.create_table(
        'resources',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, index=True),
        sa.Column('module_path', sa.String(255), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=False, index=True),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('variables', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('correlation_id', sa.String(100), nullable=True),
        sa.Column('auto_apply', sa.String(5), nullable=False),
        sa.Column('environment_id', sa.String(36), sa.ForeignKey('environments.id'), nullable=False, index=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('init_execution_id', sa.String(36), nullable=True),
        sa.Column('plan_execution_id', sa.String(36), nullable=True),
        sa.Column('apply_execution_id', sa.String(36), nullable=True),
        schema='app_schema'
    )
    
    # Create indexes
    op.create_index('ix_resources_name', 'resources', ['name'], schema='app_schema')
    op.create_index('ix_resources_resource_type', 'resources', ['resource_type'], schema='app_schema')
    op.create_index('ix_resources_environment_id', 'resources', ['environment_id'], schema='app_schema')


def downgrade():
    # Drop resources table
    op.drop_table('resources', schema='app_schema') 
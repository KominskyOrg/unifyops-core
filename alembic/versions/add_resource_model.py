"""Add resource model and update environment model

Revision ID: 0002
Create Date: 2025-04-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = '0002'
down_revision = None  # Update this with the actual previous migration ID
branch_labels = None
depends_on = None


def column_exists(conn, table, column):
    """Check if a column exists in a table"""
    return conn.execute(
        text(
            """
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = :table AND column_name = :column
            """
        ),
        {"table": table, "column": column}
    ).scalar() is not None


def index_exists(conn, index_name):
    """Check if an index exists"""
    return conn.execute(
        text(
            """
            SELECT 1 FROM pg_indexes 
            WHERE indexname = :indexname
            """
        ),
        {"indexname": index_name}
    ).scalar() is not None


def upgrade():
    # Create a raw connection to run direct queries
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    schema = None  # Use default schema
    
    # 1. Check if the environments table exists
    if not inspector.has_table('environments', schema):
        # Create environments table if it doesn't exist
        op.create_table(
            'environments',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('name', sa.String(255), nullable=False, index=True),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('status', sa.String(50), nullable=False),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('correlation_id', sa.String(100), nullable=True),
            sa.Column('global_variables', sa.JSON(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True)
        )
        
        # Only create this index if the table was just created
        if not index_exists(conn, 'ix_environments_name'):
            op.create_index('ix_environments_name', 'environments', ['name'])
    else:
        # Environments table exists, modify it to match new schema
        # Handle each column individually for better error control
        
        try:
            # Check and add description column if it doesn't exist
            if not column_exists(conn, 'environments', 'description'):
                op.add_column('environments', sa.Column('description', sa.Text(), nullable=True))
        except Exception as e:
            print(f"Could not add description column: {e}")
        
        try:
            # Check and add global_variables column if it doesn't exist
            if not column_exists(conn, 'environments', 'global_variables'):
                op.add_column('environments', sa.Column('global_variables', sa.JSON(), nullable=True))
        except Exception as e:
            print(f"Could not add global_variables column: {e}")
            
    # 2. Create resources table if it doesn't exist
    if not inspector.has_table('resources', schema):
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
            sa.Column('apply_execution_id', sa.String(36), nullable=True)
        )
        
        # Create indexes for better query performance
        if not index_exists(conn, 'ix_resources_environment_id'):
            op.create_index('ix_resources_environment_id', 'resources', ['environment_id'])
        
        if not index_exists(conn, 'ix_resources_resource_type'):
            op.create_index('ix_resources_resource_type', 'resources', ['resource_type'])
        
        if not index_exists(conn, 'ix_resources_name'):
            op.create_index('ix_resources_name', 'resources', ['name'])


def downgrade():
    # Drop the resources table if it exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    schema = None  # Use default schema
    
    if inspector.has_table('resources', schema):
        op.drop_table('resources')
    
    # Revert changes to environments table if it exists
    if inspector.has_table('environments', schema):
        try:
            if column_exists(conn, 'environments', 'description'):
                op.drop_column('environments', 'description')
        except Exception as e:
            print(f"Could not drop description column: {e}")
            
        try:
            if column_exists(conn, 'environments', 'global_variables'):
                op.drop_column('environments', 'global_variables')
        except Exception as e:
            print(f"Could not drop global_variables column: {e}")

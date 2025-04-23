"""add_user_tables

Revision ID: 99527851ee1d
Revises: d72117ff249c
Create Date: 2025-04-16 22:07:38.849881

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '99527851ee1d'
down_revision = 'd72117ff249c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table('users',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=True),
        sa.Column('last_name', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('is_superuser', sa.Boolean(), nullable=True),
        sa.Column('organization_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['app_schema.organizations.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username'),
        schema='app_schema'
    )
    
    op.create_index(op.f('ix_app_schema_users_email'), 'users', ['email'], unique=True, schema='app_schema')
    op.create_index(op.f('ix_app_schema_users_username'), 'users', ['username'], unique=True, schema='app_schema')
    
    # Create user_teams table (association table)
    op.create_table('user_teams',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('team_id', sa.String(length=36), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['team_id'], ['app_schema.teams.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['app_schema.users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='app_schema'
    )
    
    # Create tokens table
    op.create_table('tokens',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('refresh_token', sa.String(length=255), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('is_revoked', sa.Boolean(), nullable=True),
        sa.Column('client_info', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['app_schema.users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='app_schema'
    )
    
    op.create_index(op.f('ix_app_schema_tokens_refresh_token'), 'tokens', ['refresh_token'], unique=False, schema='app_schema')


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index(op.f('ix_app_schema_tokens_refresh_token'), table_name='tokens', schema='app_schema')
    op.drop_table('tokens', schema='app_schema')
    op.drop_table('user_teams', schema='app_schema')
    op.drop_index(op.f('ix_app_schema_users_username'), table_name='users', schema='app_schema')
    op.drop_index(op.f('ix_app_schema_users_email'), table_name='users', schema='app_schema')
    op.drop_table('users', schema='app_schema') 
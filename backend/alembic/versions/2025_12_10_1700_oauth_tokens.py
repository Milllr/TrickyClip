"""add oauth_tokens table

Revision ID: oauth_tokens_001
Revises: 2025_12_10_0001
Create Date: 2025-12-10 17:00:00

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = 'oauth_tokens_001'
down_revision = '2025_12_10_0001'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'oauth_tokens',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_identifier', sa.String(255), unique=True, nullable=False),
        sa.Column('access_token', sa.Text(), nullable=False),
        sa.Column('refresh_token', sa.Text(), nullable=False),
        sa.Column('token_expiry', sa.DateTime(), nullable=False),
        sa.Column('scopes', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now())
    )
    op.create_index('ix_oauth_tokens_user_identifier', 'oauth_tokens', ['user_identifier'])


def downgrade():
    op.drop_index('ix_oauth_tokens_user_identifier', 'oauth_tokens')
    op.drop_table('oauth_tokens')


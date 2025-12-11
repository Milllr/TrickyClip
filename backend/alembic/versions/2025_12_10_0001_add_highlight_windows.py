"""add highlight_windows table for ml training

Revision ID: 2025_12_10_0001
Revises: 2025_12_02_0001
Create Date: 2025-12-10 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2025_12_10_0001'
down_revision = '2025_12_02_0001'
branch_labels = None
depends_on = None


def upgrade():
    # create highlight_windows table
    op.execute("""
        CREATE TABLE IF NOT EXISTS highlight_windows (
            id UUID PRIMARY KEY,
            original_file_id UUID REFERENCES original_files(id),
            start_sec FLOAT NOT NULL,
            end_sec FLOAT NOT NULL,
            label VARCHAR(20) NOT NULL,
            source VARCHAR(50) NOT NULL,
            created_at TIMESTAMP NOT NULL
        );
    """)
    
    # create indexes
    op.execute("CREATE INDEX IF NOT EXISTS ix_highlight_windows_label ON highlight_windows(label);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_highlight_windows_original_file_id ON highlight_windows(original_file_id);")


def downgrade():
    op.drop_table('highlight_windows')



"""add cameras table and location coordinates

Revision ID: cameras_coords_001
Revises: locations_001
Create Date: 2026-01-17 01:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'cameras_coords_001'
down_revision = 'locations_001'
branch_labels = None
depends_on = None


def upgrade():
    # create cameras table
    op.create_table(
        'cameras',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), unique=True, nullable=False),
        sa.Column('slug', sa.String(255), unique=True, nullable=False),
        sa.Column('device_type', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now())
    )
    op.create_index('ix_cameras_name', 'cameras', ['name'])
    op.create_index('ix_cameras_slug', 'cameras', ['slug'])
    op.create_index('ix_cameras_device_type', 'cameras', ['device_type'])
    
    # add camera_ref_id FK to final_clips
    op.add_column('final_clips', sa.Column('camera_ref_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        'fk_final_clips_camera_ref_id',
        'final_clips',
        'cameras',
        ['camera_ref_id'],
        ['id']
    )
    
    # add coordinates and address to locations
    op.add_column('locations', sa.Column('latitude', sa.Float(), nullable=True))
    op.add_column('locations', sa.Column('longitude', sa.Float(), nullable=True))
    op.add_column('locations', sa.Column('address', sa.String(500), nullable=True))


def downgrade():
    # remove location coordinates
    op.drop_column('locations', 'address')
    op.drop_column('locations', 'longitude')
    op.drop_column('locations', 'latitude')
    
    # remove camera_ref_id from final_clips
    op.drop_constraint('fk_final_clips_camera_ref_id', 'final_clips', type_='foreignkey')
    op.drop_column('final_clips', 'camera_ref_id')
    
    # drop cameras table
    op.drop_index('ix_cameras_device_type', 'cameras')
    op.drop_index('ix_cameras_slug', 'cameras')
    op.drop_index('ix_cameras_name', 'cameras')
    op.drop_table('cameras')


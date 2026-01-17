"""add locations table, clip_people junction, and location_id to final_clips

Revision ID: locations_001
Revises: oauth_tokens_001
Create Date: 2026-01-17 00:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'locations_001'
down_revision = 'oauth_tokens_001'
branch_labels = None
depends_on = None


def upgrade():
    # create locations table
    op.create_table(
        'locations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), unique=True, nullable=False),
        sa.Column('slug', sa.String(255), unique=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now())
    )
    op.create_index('ix_locations_name', 'locations', ['name'])
    op.create_index('ix_locations_slug', 'locations', ['slug'])
    
    # create clip_people junction table for multi-person clips
    op.create_table(
        'clip_people',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('clip_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('final_clips.id'), nullable=False),
        sa.Column('person_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('people.id'), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='1')
    )
    op.create_index('ix_clip_people_clip_id', 'clip_people', ['clip_id'])
    op.create_index('ix_clip_people_person_id', 'clip_people', ['person_id'])
    op.create_index('ix_clip_people_priority', 'clip_people', ['priority'])
    
    # add location_id to final_clips
    op.add_column('final_clips', sa.Column('location_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        'fk_final_clips_location_id',
        'final_clips',
        'locations',
        ['location_id'],
        ['id']
    )


def downgrade():
    # remove location_id from final_clips
    op.drop_constraint('fk_final_clips_location_id', 'final_clips', type_='foreignkey')
    op.drop_column('final_clips', 'location_id')
    
    # drop clip_people table
    op.drop_index('ix_clip_people_priority', 'clip_people')
    op.drop_index('ix_clip_people_person_id', 'clip_people')
    op.drop_index('ix_clip_people_clip_id', 'clip_people')
    op.drop_table('clip_people')
    
    # drop locations table
    op.drop_index('ix_locations_slug', 'locations')
    op.drop_index('ix_locations_name', 'locations')
    op.drop_table('locations')


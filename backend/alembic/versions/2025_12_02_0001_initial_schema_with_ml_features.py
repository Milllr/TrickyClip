"""add ml features, job tracking, and drive integration

Revision ID: 001_ml_features
Revises: 
Create Date: 2025-12-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers
revision: str = '001_ml_features'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # add new fields to original_files table
    op.add_column('original_files', sa.Column('processing_status', sa.String(), nullable=False, server_default='pending'))
    op.add_column('original_files', sa.Column('analysis_progress_percent', sa.Integer(), nullable=False, server_default='0'))
    
    op.create_index('ix_original_files_processing_status', 'original_files', ['processing_status'])
    
    # add new fields to candidate_segments table
    op.add_column('candidate_segments', sa.Column('confidence_score', sa.Float(), nullable=False, server_default='0.5'))
    op.add_column('candidate_segments', sa.Column('detection_method', sa.String(), nullable=False, server_default='basic'))
    
    op.create_index('ix_candidate_segments_detection_method', 'candidate_segments', ['detection_method'])
    
    # add new fields to final_clips table
    op.add_column('final_clips', sa.Column('drive_url', sa.String(), nullable=True))
    op.add_column('final_clips', sa.Column('is_uploaded_to_drive', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('final_clips', sa.Column('clip_hash', sa.String(), nullable=True))
    
    op.create_index('ix_final_clips_clip_hash', 'final_clips', ['clip_hash'])
    
    # create jobs table
    op.create_table(
        'jobs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('rq_job_id', sa.String(), nullable=False),
        sa.Column('job_type', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('file_id', sa.UUID(), nullable=True),
        sa.Column('clip_id', sa.UUID(), nullable=True),
        sa.Column('progress_percent', sa.Integer(), nullable=False),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('rq_job_id')
    )
    
    op.create_index('ix_jobs_rq_job_id', 'jobs', ['rq_job_id'], unique=True)
    op.create_index('ix_jobs_job_type', 'jobs', ['job_type'])
    op.create_index('ix_jobs_status', 'jobs', ['status'])
    op.create_index('ix_jobs_file_id', 'jobs', ['file_id'])
    op.create_index('ix_jobs_clip_id', 'jobs', ['clip_id'])
    op.create_index('ix_jobs_created_at', 'jobs', ['created_at'])


def downgrade() -> None:
    # remove jobs table
    op.drop_index('ix_jobs_created_at', table_name='jobs')
    op.drop_index('ix_jobs_clip_id', table_name='jobs')
    op.drop_index('ix_jobs_file_id', table_name='jobs')
    op.drop_index('ix_jobs_status', table_name='jobs')
    op.drop_index('ix_jobs_job_type', table_name='jobs')
    op.drop_index('ix_jobs_rq_job_id', table_name='jobs')
    op.drop_table('jobs')
    
    # remove final_clips fields
    op.drop_index('ix_final_clips_clip_hash', table_name='final_clips')
    op.drop_column('final_clips', 'clip_hash')
    op.drop_column('final_clips', 'is_uploaded_to_drive')
    op.drop_column('final_clips', 'drive_url')
    
    # remove candidate_segments fields
    op.drop_index('ix_candidate_segments_detection_method', table_name='candidate_segments')
    op.drop_column('candidate_segments', 'detection_method')
    op.drop_column('candidate_segments', 'confidence_score')
    
    # remove original_files fields
    op.drop_index('ix_original_files_processing_status', table_name='original_files')
    op.drop_column('original_files', 'analysis_progress_percent')
    op.drop_column('original_files', 'processing_status')




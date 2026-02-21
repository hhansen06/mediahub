"""add persons and face_detections tables

Revision ID: 003
Revises: 002
Create Date: 2026-02-19 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create persons table
    op.create_table(
        'persons',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('face_encoding', sa.LargeBinary(), nullable=False),
        sa.Column('sample_face_image_s3_key', sa.String(1000), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_persons_id', 'persons', ['id'])
    op.create_index('ix_persons_name', 'persons', ['name'])
    op.create_index('ix_persons_user_id', 'persons', ['user_id'])
    
    # Create face_detections table
    op.create_table(
        'face_detections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('top', sa.Integer(), nullable=False),
        sa.Column('right', sa.Integer(), nullable=False),
        sa.Column('bottom', sa.Integer(), nullable=False),
        sa.Column('left', sa.Integer(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('media_id', sa.Integer(), nullable=False),
        sa.Column('person_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['media_id'], ['media.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_face_detections_id', 'face_detections', ['id'])
    op.create_index('ix_face_detections_media_id', 'face_detections', ['media_id'])
    op.create_index('ix_face_detections_person_id', 'face_detections', ['person_id'])


def downgrade() -> None:
    op.drop_index('ix_face_detections_person_id', table_name='face_detections')
    op.drop_index('ix_face_detections_media_id', table_name='face_detections')
    op.drop_index('ix_face_detections_id', table_name='face_detections')
    op.drop_table('face_detections')
    
    op.drop_index('ix_persons_user_id', table_name='persons')
    op.drop_index('ix_persons_name', table_name='persons')
    op.drop_index('ix_persons_id', table_name='persons')
    op.drop_table('persons')

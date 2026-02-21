"""Initial migration - create users, collections, and media tables

Revision ID: 001
Revises: 
Create Date: 2026-02-18 23:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(255), nullable=False),
        sa.Column('username', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
        sa.UniqueConstraint('email')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    
    # Create collections table
    op.create_table(
        'collections',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('location', sa.String(500), nullable=True),
        sa.Column('date', sa.Date(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('owner_id', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_collections_id'), 'collections', ['id'], unique=False)
    op.create_index(op.f('ix_collections_name'), 'collections', ['name'], unique=False)
    
    # Create media table
    op.create_table(
        'media',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('filename', sa.String(500), nullable=False),
        sa.Column('original_filename', sa.String(500), nullable=False),
        sa.Column('media_type', sa.Enum('IMAGE', 'VIDEO', name='mediatype'), nullable=False),
        sa.Column('mime_type', sa.String(100), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=False),
        sa.Column('s3_key', sa.String(1000), nullable=False),
        sa.Column('s3_bucket', sa.String(255), nullable=False),
        sa.Column('thumbnail_s3_key', sa.String(1000), nullable=True),
        sa.Column('collection_id', sa.Integer(), nullable=False),
        sa.Column('uploaded_by', sa.String(255), nullable=False),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('camera_make', sa.String(255), nullable=True),
        sa.Column('camera_model', sa.String(255), nullable=True),
        sa.Column('lens_model', sa.String(255), nullable=True),
        sa.Column('focal_length', sa.String(50), nullable=True),
        sa.Column('aperture', sa.String(50), nullable=True),
        sa.Column('iso', sa.Integer(), nullable=True),
        sa.Column('shutter_speed', sa.String(50), nullable=True),
        sa.Column('taken_at', sa.DateTime(), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('altitude', sa.Float(), nullable=True),
        sa.Column('duration', sa.Float(), nullable=True),
        sa.Column('video_codec', sa.String(100), nullable=True),
        sa.Column('audio_codec', sa.String(100), nullable=True),
        sa.Column('additional_metadata', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['collection_id'], ['collections.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('s3_key')
    )
    op.create_index(op.f('ix_media_id'), 'media', ['id'], unique=False)
    op.create_index(op.f('ix_media_media_type'), 'media', ['media_type'], unique=False)
    op.create_index(op.f('ix_media_collection_id'), 'media', ['collection_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_media_collection_id'), table_name='media')
    op.drop_index(op.f('ix_media_media_type'), table_name='media')
    op.drop_index(op.f('ix_media_id'), table_name='media')
    op.drop_table('media')
    
    op.drop_index(op.f('ix_collections_name'), table_name='collections')
    op.drop_index(op.f('ix_collections_id'), table_name='collections')
    op.drop_table('collections')
    
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_table('users')

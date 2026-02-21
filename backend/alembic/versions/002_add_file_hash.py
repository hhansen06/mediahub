"""add file_hash to media

Revision ID: 002
Revises: 001
Create Date: 2026-02-19 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add file_hash column
    op.add_column('media', sa.Column('file_hash', sa.String(64), nullable=True))
    
    # Create index on file_hash
    op.create_index('ix_media_file_hash', 'media', ['file_hash'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_media_file_hash', table_name='media')
    op.drop_column('media', 'file_hash')

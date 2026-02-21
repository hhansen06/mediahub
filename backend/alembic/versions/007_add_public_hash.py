"""Add public_hash field to media table for secure sharing

Revision ID: 007
Revises: 006
Create Date: 2026-02-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('media', sa.Column('public_hash', sa.String(64), nullable=True))
    op.create_index(op.f('ix_media_public_hash'), 'media', ['public_hash'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_media_public_hash'), table_name='media')
    op.drop_column('media', 'public_hash')

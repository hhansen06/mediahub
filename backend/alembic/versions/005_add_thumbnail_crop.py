"""add thumbnail crop fields

Revision ID: 005
Revises: 004
Create Date: 2026-02-20

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add thumbnail crop coordinate fields to media table
    op.add_column('media', sa.Column('crop_x', sa.Float(), nullable=True))
    op.add_column('media', sa.Column('crop_y', sa.Float(), nullable=True))
    op.add_column('media', sa.Column('crop_width', sa.Float(), nullable=True))
    op.add_column('media', sa.Column('crop_height', sa.Float(), nullable=True))


def downgrade() -> None:
    # Remove thumbnail crop coordinate fields
    op.drop_column('media', 'crop_height')
    op.drop_column('media', 'crop_width')
    op.drop_column('media', 'crop_y')
    op.drop_column('media', 'crop_x')

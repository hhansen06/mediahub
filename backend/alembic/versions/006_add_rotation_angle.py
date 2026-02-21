"""add rotation_angle field

Revision ID: 006
Revises: 005
Create Date: 2026-02-20

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add rotation_angle field to media table
    op.add_column('media', sa.Column('rotation_angle', sa.Integer(), nullable=True, server_default='0'))


def downgrade() -> None:
    # Remove rotation_angle field
    op.drop_column('media', 'rotation_angle')

"""Add watermark_text field to users table

Revision ID: 004
Revises: 003
Create Date: 2026-02-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('watermark_text', sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'watermark_text')

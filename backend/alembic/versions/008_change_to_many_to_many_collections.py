"""Change media-collection relationship to many-to-many

Revision ID: 008
Revises: 007
Create Date: 2026-02-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the new many-to-many junction table
    op.create_table(
        'media_collections',
        sa.Column('media_id', sa.Integer(), nullable=False),
        sa.Column('collection_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['collection_id'], ['collections.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['media_id'], ['media.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('media_id', 'collection_id')
    )
    
    # Migrate existing data: copy collection_id values to new junction table
    # This ensures each media stays in its current collection
    op.execute(
        sa.text("""
            INSERT INTO media_collections (media_id, collection_id, created_at)
            SELECT id, collection_id, NOW() FROM media
            WHERE collection_id IS NOT NULL
        """)
    )
    
    # Drop the old foreign key constraint
    op.drop_constraint('media_ibfk_1', 'media', type_='foreignkey')
    
    # Drop the old collection_id column
    op.drop_column('media', 'collection_id')


def downgrade() -> None:
    # Add back the collection_id column
    op.add_column('media', sa.Column('collection_id', sa.Integer(), nullable=False))
    
    # Restore data from junction table (each media gets its first collection)
    op.execute(
        sa.text("""
            UPDATE media m
            SET collection_id = (
                SELECT collection_id FROM media_collections
                WHERE media_id = m.id
                LIMIT 1
            )
        """)
    )
    
    # Add back the foreign key constraint
    op.create_foreign_key('media_ibfk_1', 'media', 'collections', ['collection_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_media_collection_id', 'media', ['collection_id'], unique=False)
    
    # Drop the junction table
    op.drop_table('media_collections')

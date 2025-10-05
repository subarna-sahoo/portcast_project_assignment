"""Add WordFrequency table

Revision ID: d4f2a9c8e1b2
Revises: cb3e05b5b253
Create Date: 2025-10-05 16:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4f2a9c8e1b2'
down_revision: Union[str, None] = 'cb3e05b5b253'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create word_frequencies table
    op.create_table('word_frequencies',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('word', sa.String(length=100), nullable=False),
    sa.Column('frequency', sa.Integer(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('word')
    )
    op.create_index(op.f('ix_word_frequencies_id'), 'word_frequencies', ['id'], unique=False)
    op.create_index(op.f('ix_word_frequencies_word'), 'word_frequencies', ['word'], unique=True)


def downgrade() -> None:
    # Drop word_frequencies table
    op.drop_index(op.f('ix_word_frequencies_word'), table_name='word_frequencies')
    op.drop_index(op.f('ix_word_frequencies_id'), table_name='word_frequencies')
    op.drop_table('word_frequencies')

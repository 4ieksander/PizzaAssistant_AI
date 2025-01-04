"""Transcript history logs

Revision ID: 45c01764cc3f
Revises: d3cb75a21bf4
Create Date: 2025-01-04 17:03:07.708254

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '45c01764cc3f'
down_revision: Union[str, None] = 'd3cb75a21bf4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('transcription_logs',
    sa.Column('_id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('content', sa.String(), nullable=False),
    sa.Column('updated_slots', sa.String(), nullable=True),
    sa.Column('order_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['order_id'], ['orders._id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('_id')
    )
    op.create_index(op.f('ix_transcription_logs_id'), 'transcription_logs', ['_id'], unique=False)
    op.create_table('order_transcripts',
    sa.Column('order_id', sa.Integer(), nullable=False),
    sa.Column('transcript_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['order_id'], ['orders._id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['transcript_id'], ['transcription_logs._id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('order_id', 'transcript_id')
    )
    op.drop_column('doughs', 'without_gluten')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('doughs', sa.Column('without_gluten', sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.drop_table('order_transcripts')
    op.drop_index(op.f('ix_transcription_logs_id'), table_name='transcription_logs')
    op.drop_table('transcription_logs')
    # ### end Alembic commands ###

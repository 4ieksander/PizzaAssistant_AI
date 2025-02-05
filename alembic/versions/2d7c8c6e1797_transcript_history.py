"""Transcript history

Revision ID: 2d7c8c6e1797
Revises: fd67ccb3e3e6
Create Date: 2025-01-04 16:44:51.202638

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2d7c8c6e1797'
down_revision: Union[str, None] = 'fd67ccb3e3e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('transcripts', sa.Column('updated_slots', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('transcripts', 'updated_slots')
    # ### end Alembic commands ###

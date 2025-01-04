"""piza doughs

Revision ID: b316bd4cf563
Revises: cadc52c6610c
Create Date: 2025-01-04 09:37:14.970785

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b316bd4cf563'
down_revision: Union[str, None] = 'cadc52c6610c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('pizza_doughs',
    sa.Column('pizza_id', sa.Integer(), nullable=False),
    sa.Column('dough_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['dough_id'], ['doughs.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['pizza_id'], ['pizzas.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('pizza_id', 'dough_id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('pizza_doughs')
    # ### end Alembic commands ###

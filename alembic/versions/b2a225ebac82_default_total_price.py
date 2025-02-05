"""default TOTAL PRICE

Revision ID: b2a225ebac82
Revises: ab41eccc20bb
Create Date: 2024-12-08 15:51:16.902522

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2a225ebac82'
down_revision: Union[str, None] = 'ab41eccc20bb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('orders', 'total_price',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               nullable=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('orders', 'total_price',
               existing_type=sa.DOUBLE_PRECISION(precision=53),
               nullable=True)
    # ### end Alembic commands ###

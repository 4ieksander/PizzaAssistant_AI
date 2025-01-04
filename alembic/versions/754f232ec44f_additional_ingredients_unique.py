"""additional-ingredients UNIQUE

Revision ID: 754f232ec44f
Revises: b11c7a3b7f13
Create Date: 2025-01-04 13:07:26.289042

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '754f232ec44f'
down_revision: Union[str, None] = 'b11c7a3b7f13'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_unique_constraint('_order_pizza_ingredient_quantity_uc', 'additional_ingredients', ['order_pizza_id', 'ingredient_id', 'quantity'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('_order_pizza_ingredient_quantity_uc', 'additional_ingredients', type_='unique')
    # ### end Alembic commands ###

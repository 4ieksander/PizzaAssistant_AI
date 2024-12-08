"""zaraz nie wytrzymam.... #2

Revision ID: 0db31102c3c9
Revises: 3e4e97ff3eab
Create Date: 2024-12-08 02:10:51.330110

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0db31102c3c9'
down_revision: Union[str, None] = '3e4e97ff3eab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('clients', sa.Column('address', sa.String(), nullable=True))
    op.drop_column('clients', 'address_id')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('clients', sa.Column('address_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.drop_column('clients', 'address')
    # ### end Alembic commands ###

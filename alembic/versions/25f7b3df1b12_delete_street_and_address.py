"""delete street and address

Revision ID: 25f7b3df1b12
Revises: 8b80c20e8ab2
Create Date: 2024-12-08 08:56:40.452480

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '25f7b3df1b12'
down_revision: Union[str, None] = '8b80c20e8ab2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###

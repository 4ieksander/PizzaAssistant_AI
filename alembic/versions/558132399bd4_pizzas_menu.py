"""Pizzas -> Menu

Revision ID: 558132399bd4
Revises: 158844daac31
Create Date: 2024-11-23 12:06:19.250920

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '558132399bd4'
down_revision: Union[str, None] = '158844daac31'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

"""Proposal of full list models with relationships

Revision ID: 056d43ecffff
Revises: 558132399bd4
Create Date: 2024-11-23 13:43:11.526723

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '056d43ecffff'
down_revision: Union[str, None] = '558132399bd4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

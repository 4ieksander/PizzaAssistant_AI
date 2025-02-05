"""zaraz nie wytrzymam....

Revision ID: 3e4e97ff3eab
Revises: d4ed0124ae67
Create Date: 2024-12-08 02:04:48.848876

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3e4e97ff3eab'
down_revision: Union[str, None] = 'd4ed0124ae67'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP TABLE addresses CASCADE")
    op.execute("DROP TABLE streets CASCADE")

    # ### commands auto generated by Alembic - please adjust! ###
    #
    # op.drop_index('ix_streets_id', table_name='streets')
    # op.drop_table('streets')
    # op.add_column('clients', sa.Column('address', sa.String(), nullable=True))
    # op.drop_constraint('clients_address_id_fkey', 'clients', type_='foreignkey')
    # op.drop_column('clients', 'address_id')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('clients', sa.Column('address_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.create_foreign_key('clients_address_id_fkey', 'clients', 'addresses', ['address_id'], ['id'])
    op.drop_column('clients', 'address')
    op.create_table('streets',
    sa.Column('id', sa.INTEGER(), server_default=sa.text("nextval('streets_id_seq'::regclass)"), autoincrement=True, nullable=False),
    sa.Column('name', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id', name='streets_pkey'),
    postgresql_ignore_search_path=False
    )
    op.create_index('ix_streets_id', 'streets', ['id'], unique=False)
    op.create_table('addresses',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('street_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('building_number', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('apartment_number', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('client_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['client_id'], ['clients.id'], name='addresses_client_id_fkey'),
    sa.ForeignKeyConstraint(['street_id'], ['streets.id'], name='addresses_street_id_fkey'),
    sa.PrimaryKeyConstraint('id', name='addresses_pkey')
    )
    op.create_index('ix_addresses_id', 'addresses', ['id'], unique=False)
    # ### end Alembic commands ###

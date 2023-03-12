"""Add column to driver table

Revision ID: 1fba501b1807
Revises: 8076a0692fc3
Create Date: 2023-03-12 11:11:55.342964

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1fba501b1807'
down_revision = '8076a0692fc3'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('driver', schema=None) as batch_op:
        batch_op.add_column(sa.Column('season_active', sa.Boolean(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('driver', schema=None) as batch_op:
        batch_op.drop_column('season_active')

    # ### end Alembic commands ###
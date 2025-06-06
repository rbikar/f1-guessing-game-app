"""move to float on Bet.result

Revision ID: d3f5c0a1f41d
Revises: 
Create Date: 2025-03-19 14:33:04.870113

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd3f5c0a1f41d'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('bet', schema=None) as batch_op:
        batch_op.alter_column('result',
               existing_type=sa.INTEGER(),
               type_=sa.Float(),
               existing_nullable=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('bet', schema=None) as batch_op:
        batch_op.alter_column('result',
               existing_type=sa.Float(),
               type_=sa.INTEGER(),
               existing_nullable=False)

    # ### end Alembic commands ###

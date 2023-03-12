"""Add season_bet table

Revision ID: 8076a0692fc3
Revises: 
Create Date: 2023-03-12 10:53:35.538988

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8076a0692fc3'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('season_bet',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('value', sa.String(length=50), nullable=True),
    sa.Column('rank', sa.Integer(), nullable=True),
    sa.Column('type', sa.String(length=50), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('season_bet')
    # ### end Alembic commands ###

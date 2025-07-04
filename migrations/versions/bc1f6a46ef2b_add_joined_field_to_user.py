"""Add joined field to User

Revision ID: bc1f6a46ef2b
Revises: 8a54813153e4
Create Date: 2025-06-26 23:09:49.850507

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bc1f6a46ef2b'
down_revision = '8a54813153e4'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('joined', sa.DateTime(), nullable=True))
        batch_op.drop_column('created_at')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('created_at', sa.DATETIME(), nullable=True))
        batch_op.drop_column('joined')

    # ### end Alembic commands ###

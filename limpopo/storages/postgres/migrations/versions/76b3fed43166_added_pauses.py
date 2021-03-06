"""Added pauses

Revision ID: 76b3fed43166
Revises: 100f64d6906c
Create Date: 2020-12-18 03:31:18.583432

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '76b3fed43166'
down_revision = '100f64d6906c'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('dialogue_pauses',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('dialog_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('active', sa.Boolean(), server_default=sa.text('true'), nullable=True),
    sa.ForeignKeyConstraint(['dialog_id'], ['dialogs.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('dialog_id', 'active', name='one_pause_active')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('dialogue_pauses')
    # ### end Alembic commands ###

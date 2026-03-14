"""Add reminder_level and reminder_date to invoices (Mahnwesen)

Revision ID: 007
Revises: 006
Create Date: 2026-03-10

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("invoices", sa.Column("reminder_level", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("invoices", sa.Column("reminder_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("invoices", "reminder_date")
    op.drop_column("invoices", "reminder_level")

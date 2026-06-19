"""initial schema

Baseline migration. To stay in lockstep with the SQLAlchemy models (and avoid
drift in a hackathon-scoped codebase) this baseline creates every table from
``Base.metadata``. Subsequent migrations should use explicit ``op`` operations.

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-19
"""
from alembic import op

from app.database import Base
import app.models  # noqa: F401  register models on Base.metadata

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)

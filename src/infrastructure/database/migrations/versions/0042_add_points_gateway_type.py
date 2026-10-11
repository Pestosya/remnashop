from typing import Sequence, Union

from alembic import op

revision: str = "0042"
down_revision: Union[str, None] = "0041"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Transactions paid with referral points are stored with this gateway type."""
    op.execute("ALTER TYPE payment_gateway_type ADD VALUE IF NOT EXISTS 'POINTS'")


def downgrade() -> None:
    pass

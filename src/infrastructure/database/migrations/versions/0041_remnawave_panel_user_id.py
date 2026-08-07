from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0041"
down_revision: Union[str, None] = "0040"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Move subscriptions from the panel's user UUID to its numeric user id.

    Remnawave 3.0 dropped `uuid` from the user API entirely: users are addressed
    by `id` and the old UUID is not returned by any endpoint, so it cannot be
    translated here. The existing values are preserved in `remna_uuid` for
    auditing, `user_remna_id` starts out NULL, and the application re-links each
    row against the panel (by subscription short UUID, then by username).
    """
    op.alter_column(
        "subscriptions",
        "user_remna_id",
        new_column_name="remna_uuid",
        existing_type=sa.UUID(),
        existing_nullable=False,
        nullable=True,
    )
    # The index follows the renamed column, so free the old name before reusing
    # it for the new one.
    op.execute("ALTER INDEX ix_subscriptions_user_remna_id RENAME TO ix_subscriptions_remna_uuid")

    op.add_column(
        "subscriptions",
        sa.Column("user_remna_id", sa.BigInteger(), nullable=True),
    )
    op.create_index(
        "ix_subscriptions_user_remna_id",
        "subscriptions",
        ["user_remna_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_subscriptions_user_remna_id", table_name="subscriptions")
    op.drop_column("subscriptions", "user_remna_id")

    op.execute("ALTER INDEX ix_subscriptions_remna_uuid RENAME TO ix_subscriptions_user_remna_id")
    op.alter_column(
        "subscriptions",
        "remna_uuid",
        new_column_name="user_remna_id",
        existing_type=sa.UUID(),
        existing_nullable=True,
        nullable=False,
    )

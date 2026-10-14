"""privacidad: aceptación de términos y cuentas eliminadas (feature 028)

Agrega una tabla y un valor al enum `accountstatus`. Volver a la versión anterior del código
es seguro mientras no haya cuentas eliminadas (el downgrade las bloquea si existen).

Revision ID: c3d4e5f6a7b9
Revises: b2c3d4e5f6a8
Create Date: 2026-10-14 10:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'c3d4e5f6a7b9'
down_revision: str | None = 'b2c3d4e5f6a8'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'terms_acceptance',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('app_user.id'), nullable=False),
        sa.Column('version', sa.String(20), nullable=False),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_terms_acceptance_user_id', 'terms_acceptance', ['user_id'])
    if op.get_bind().dialect.name == 'postgresql':
        with op.get_context().autocommit_block():
            op.execute("ALTER TYPE accountstatus ADD VALUE IF NOT EXISTS 'deleted'")


def downgrade() -> None:
    if op.get_bind().dialect.name == 'postgresql':
        bind = op.get_bind()
        n = bind.execute(sa.text("SELECT count(*) FROM account WHERE status = 'deleted'")).scalar()
        if n:
            raise RuntimeError("Hay cuentas eliminadas: no se puede quitar el valor 'deleted'")
        op.execute("ALTER TABLE account ALTER COLUMN status DROP DEFAULT")
        op.execute("ALTER TYPE accountstatus RENAME TO accountstatus_old")
        op.execute("CREATE TYPE accountstatus AS ENUM ('active', 'disabled')")
        op.execute(
            "ALTER TABLE account ALTER COLUMN status TYPE accountstatus "
            "USING status::text::accountstatus"
        )
        op.execute("ALTER TABLE account ALTER COLUMN status SET DEFAULT 'active'")
        op.execute("DROP TYPE accountstatus_old")
    op.drop_index('ix_terms_acceptance_user_id', table_name='terms_acceptance')
    op.drop_table('terms_acceptance')

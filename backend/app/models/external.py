"""Metadata-only references to objects owned and migrated by Supabase."""
from sqlalchemy import Column, event
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


supabase_auth_users = Base.metadata.tables.get("auth.users")
if supabase_auth_users is None:
    from sqlalchemy import Table

    supabase_auth_users = Table(
        "users", Base.metadata,
        Column("id", UUID(as_uuid=True), primary_key=True),
        schema="auth",
        info={"supabase_managed": True},
    )


@event.listens_for(supabase_auth_users, "before_create")
def prevent_auth_table_creation(_target, _connection, **_kwargs):
    raise RuntimeError("auth.users is managed by Supabase and must never be created by SQLAlchemy")

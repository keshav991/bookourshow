from uuid import UUID
from datetime import datetime
from sqlalchemy import ForeignKey, Index, Text, DateTime, func, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models import external  # registers an external FK target; never creates auth.users


class Profile(Base):
    __tablename__ = "profiles"
    __table_args__ = (Index("idx_profiles_role", "role"),)

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        primary_key=True
    )
    full_name: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )
    role: Mapped[str] = mapped_column(
        Text,
        server_default="customer",
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("timezone('utc'::text, now())"),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("timezone('utc'::text, now())"),
        nullable=False
    )

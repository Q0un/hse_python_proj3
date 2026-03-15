from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text, TypeDecorator, func
from sqlalchemy.orm import Mapped, mapped_column, relationship


class TZDateTime(TypeDecorator):
    """Datetime column that always returns timezone-aware UTC datetimes."""
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

from .db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    login: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    pw_hash: Mapped[str] = mapped_column(String(256))
    registered_at: Mapped[datetime] = mapped_column(TZDateTime, server_default=func.now())

    urls: Mapped[list["Link"]] = relationship(back_populates="creator")


class Link(Base):
    __tablename__ = "links"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    target: Mapped[str] = mapped_column(Text, index=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), default=None)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(TZDateTime, default=None)
    visited_at: Mapped[datetime | None] = mapped_column(TZDateTime, default=None)
    hits: Mapped[int] = mapped_column(default=0)
    active: Mapped[bool] = mapped_column(default=True)

    creator: Mapped[User | None] = relationship(back_populates="urls")

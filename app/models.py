from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

TZDateTime = DateTime(timezone=True)

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

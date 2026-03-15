from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import cache
from app.models import Link
from app.tasks import expire_loop, flush_hits_loop


class _Break(BaseException):
    """Raised from mocked asyncio.sleep to exit the infinite loop."""


# Expire loop


async def test_expire_loop_deactivates(db: AsyncSession):
    link = Link(
        code="ya",
        target="https://ya.ru/",
        active=True,
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    db.add(link)
    await db.commit()

    with patch("app.tasks.asyncio.sleep", side_effect=_Break):
        with pytest.raises(_Break):
            await expire_loop()

    await db.refresh(link)
    assert link.active is False


async def test_expire_loop_stays_active(db: AsyncSession):
    link = Link(
        code="ya",
        target="https://ya.ru/",
        active=True,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db.add(link)
    await db.commit()

    with patch("app.tasks.asyncio.sleep", side_effect=_Break):
        with pytest.raises(_Break):
            await expire_loop()

    await db.refresh(link)
    assert link.active is True


async def test_expire_loop_skips_without_expires(db: AsyncSession):
    link = Link(
        code="ya",
        target="https://ya.ru/",
        active=True,
    )
    db.add(link)
    await db.commit()

    with patch("app.tasks.asyncio.sleep", side_effect=_Break):
        with pytest.raises(_Break):
            await expire_loop()

    await db.refresh(link)
    assert link.active is True


# Flush hits loop


async def test_flush_hits_syncs_to_db(db: AsyncSession):
    link = Link(code="ya", target="https://ya.ru/", active=True, hits=0)
    db.add(link)
    await db.commit()

    await cache.bump_hits("ya")
    await cache.bump_hits("ya")
    await cache.bump_hits("ya")

    with patch("app.tasks.asyncio.sleep", side_effect=_Break):
        with pytest.raises(_Break):
            await flush_hits_loop()

    await db.refresh(link)
    assert link.hits == 3
    assert link.visited_at is not None


async def test_flush_hits_empty_does_nothing(db: AsyncSession):
    with patch("app.tasks.asyncio.sleep", side_effect=_Break):
        with pytest.raises(_Break):
            await flush_hits_loop()

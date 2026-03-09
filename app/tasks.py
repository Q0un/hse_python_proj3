import asyncio
from datetime import datetime, timezone

from sqlalchemy import select

from .cache import cache
from .db import SessionLocal
from .models import Link


async def expire_loop():
    while True:
        try:
            async with SessionLocal() as db:
                now = datetime.now(timezone.utc)
                rows = await db.execute(
                    select(Link).where(
                        Link.active.is_(True),
                        Link.expires_at.isnot(None),
                        Link.expires_at <= now,
                    )
                )
                stale = rows.scalars().all()
                for lnk in stale:
                    lnk.active = False
                    await cache.drop_for(lnk.code, lnk.target)
                if stale:
                    await db.commit()
        except Exception:
            pass
        await asyncio.sleep(60)


async def flush_hits_loop():
    while True:
        try:
            pending = await cache.drain_hits()
            if pending:
                async with SessionLocal() as db:
                    for code, cnt in pending.items():
                        row = await db.execute(
                            select(Link).where(Link.code == code)
                        )
                        lnk = row.scalar_one_or_none()
                        if lnk:
                            lnk.hits += cnt
                            lnk.visited_at = datetime.now(timezone.utc)
                    await db.commit()
        except Exception:
            pass
        await asyncio.sleep(30)

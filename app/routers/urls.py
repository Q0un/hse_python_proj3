from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from pydantic import HttpUrl
import hashlib
import random
from sqlalchemy import select
import time

from ..cache import cache
from ..deps import DB, CurrentUser, OptionalUser
from ..models import Link
from ..schemas import (
    CleanupIn,
    ExpiredOut,
    ShortLinkOut,
    ShortenIn,
    StatsOut,
    UpdateTargetIn,
)
from ..settings import cfg

router = APIRouter(tags=["urls"])


async def _find_active(code: str, db) -> Link:
    row = await db.execute(
        select(Link).where(Link.code == code, Link.active.is_(True))
    )
    link = row.scalar_one_or_none()
    if link is None:
        raise HTTPException(404, "Ссылка не найдена")

    now = datetime.now(timezone.utc)
    if link.expires_at and link.expires_at <= now:
        link.active = False
        await db.commit()
        await cache.drop_for(code, link.target)
        raise HTTPException(410, "Ссылка просрочена")

    return link


def _generate_short_code(url: str) -> str:
    seed = f"{url}|{time.time_ns()}|{random.getrandbits(64)}"
    digest = hashlib.blake2b(seed.encode(), digest_size=8).hexdigest()
    return digest[: cfg.code_length]


@router.post("/links/shorten", response_model=ShortLinkOut, status_code=201)
async def shorten(body: ShortenIn, db: DB, user: OptionalUser):
    target = str(body.url)

    if body.alias:
        dup = await db.execute(select(Link).where(Link.code == body.alias))
        if dup.scalar_one_or_none():
            raise HTTPException(409, "Alias уже используется")
        code = body.alias
    else:
        for _ in range(10):
            code = _generate_short_code(target)
            dup = await db.execute(select(Link).where(Link.code == code))
            if dup.scalar_one_or_none() is None:
                break
        else:
            raise HTTPException(500, "Не удалось сгенерировать код")

    link = Link(
        code=code,
        target=target,
        owner_id=user.id if user else None,
        expires_at=body.expires_at,
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return link


@router.get("/links/search", response_model=list[ShortLinkOut])
async def search(db: DB, original_url: str = Query(..., description="URL для поиска")):
    try:
        original_url = str(HttpUrl(original_url))
    except ValueError:
        raise HTTPException(400, "Невалидный URL")
    key = f"search:{original_url}"
    hit = await cache.get_json(key)
    if hit:
        return hit

    rows = await db.execute(
        select(Link).where(Link.target == original_url, Link.active.is_(True))
    )
    found = rows.scalars().all()
    if not found:
        raise HTTPException(404, "Ничего не найдено")

    out = [ShortLinkOut.model_validate(x).model_dump(mode="json") for x in found]
    await cache.put_json(key, out)
    return out


@router.get("/links/{code}/stats", response_model=StatsOut)
async def stats(code: str, db: DB):
    key = f"stats:{code}"
    hit = await cache.get_json(key)
    if hit:
        return hit

    link = await _find_active(code, db)
    out = StatsOut.model_validate(link).model_dump(mode="json")
    await cache.put_json(key, out)
    return out


@router.get("/links/{code}")
async def follow(code: str, db: DB):
    cached_url = await cache.get_target(code)
    if cached_url:
        await cache.bump_hits(code)
        return RedirectResponse(cached_url, status_code=307)

    link = await _find_active(code, db)
    link.hits += 1
    link.visited_at = datetime.now(timezone.utc)
    await db.commit()

    await cache.set_target(code, link.target)
    return RedirectResponse(link.target, status_code=307)


@router.put("/links/{code}", response_model=ShortLinkOut)
async def update(code: str, body: UpdateTargetIn, db: DB, user: CurrentUser):
    link = await _find_active(code, db)
    if link.owner_id != user.id:
        raise HTTPException(403, "Нет прав")

    prev_target = link.target
    link.target = str(body.url)
    await db.commit()
    await db.refresh(link)
    await cache.drop_for(code, prev_target)
    return link


@router.delete("/links/{code}", status_code=status.HTTP_204_NO_CONTENT)
async def remove(code: str, db: DB, user: CurrentUser):
    link = await _find_active(code, db)
    if link.owner_id != user.id:
        raise HTTPException(403, "Нет прав")

    await cache.drop_for(code, link.target)
    await db.delete(link)
    await db.commit()


@router.get("/links-expired", response_model=list[ExpiredOut], tags=["extra"])
async def expired_history(db: DB):
    rows = await db.execute(select(Link).where(Link.active.is_(False)))
    return rows.scalars().all()


@router.post("/links-cleanup", tags=["extra"])
async def cleanup(db: DB, user: CurrentUser, body: CleanupIn | None = None):
    days = body.days if body else cfg.inactive_days_limit
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    rows = await db.execute(
        select(Link).where(
            Link.active.is_(True),
            (Link.visited_at <= cutoff)
            | (Link.visited_at.is_(None) & (Link.created_at <= cutoff)),
        )
    )
    stale = rows.scalars().all()
    for lnk in stale:
        lnk.active = False
        await cache.drop_for(lnk.code, lnk.target)
    await db.commit()
    return {"deactivated": len(stale)}

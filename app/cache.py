import json
from typing import Any

import redis.asyncio as aioredis

from .settings import cfg


class RedisCache:
    """Typed wrapper around Redis for link caching."""

    def __init__(self):
        self._pool: aioredis.Redis | None = None

    async def _r(self) -> aioredis.Redis:
        if self._pool is None:
            self._pool = aioredis.from_url(cfg.redis_url, decode_responses=True)
        return self._pool

    async def get_target(self, code: str) -> str | None:
        r = await self._r()
        return await r.get(f"url:{code}")

    async def set_target(self, code: str, url: str):
        r = await self._r()
        await r.setex(f"url:{code}", cfg.cache_ttl_sec, url)

    async def get_json(self, key: str) -> Any | None:
        r = await self._r()
        raw = await r.get(key)
        return json.loads(raw) if raw else None

    async def put_json(self, key: str, obj: Any):
        r = await self._r()
        await r.setex(key, cfg.cache_ttl_sec, json.dumps(obj, default=str))

    async def bump_hits(self, code: str):
        r = await self._r()
        await r.hincrby("pending_hits", code, 1)

    async def get_pending_hits(self, code: str) -> int:
        r = await self._r()
        val = await r.hget("pending_hits", code)
        return int(val) if val else 0

    async def drain_hits(self) -> dict[str, int]:
        r = await self._r()
        raw = await r.hgetall("pending_hits")
        if raw:
            await r.delete("pending_hits")
        return {k: int(v) for k, v in raw.items()}

    async def drop_for(self, code: str, target: str | None = None):
        keys_to_del = [f"url:{code}", f"stats:{code}"]
        if target:
            keys_to_del.append(f"search:{target}")
        r = await self._r()
        await r.delete(*keys_to_del)

    async def close(self):
        if self._pool:
            await self._pool.close()
            self._pool = None


cache = RedisCache()

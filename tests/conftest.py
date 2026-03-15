import os

os.environ.setdefault("DB_URL", "sqlite+aiosqlite://")
os.environ.setdefault("JWT_SECRET", "test-secret-key")

import fakeredis
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.cache import cache
from app.db import Base, get_session
from app.main import app
import app.tasks as tasks_mod

_engine = create_async_engine(
    "sqlite+aiosqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_Session = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


async def _override_session():
    async with _Session() as s:
        yield s


@pytest_asyncio.fixture(autouse=True)
async def _setup():
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app.dependency_overrides[get_session] = _override_session

    _orig_sl = tasks_mod.SessionLocal
    tasks_mod.SessionLocal = _Session

    fake_redis = fakeredis.FakeAsyncRedis(decode_responses=True)
    cache._pool = fake_redis

    yield

    app.dependency_overrides.clear()
    tasks_mod.SessionLocal = _orig_sl
    cache._pool = None
    await fake_redis.flushall()
    await fake_redis.aclose()

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def db():
    async with _Session() as s:
        yield s

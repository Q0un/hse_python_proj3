import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .cache import cache
from .db import Base, engine
from .routers import auth, urls
from .tasks import expire_loop, flush_hits_loop


@asynccontextmanager
async def lifespan(_app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    bg = [asyncio.create_task(expire_loop()), asyncio.create_task(flush_hits_loop())]
    yield
    for t in bg:
        t.cancel()
    await cache.close()


app = FastAPI(title="Shortener", version="1.0.0", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(urls.router)


@app.get("/ping")
async def ping():
    return "pong"

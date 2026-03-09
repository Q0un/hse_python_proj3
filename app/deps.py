from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_session
from .models import User
from .security import read_token

_oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

DB = Annotated[AsyncSession, Depends(get_session)]


async def _resolve_user(
    token: str | None = Depends(_oauth2),
    db: AsyncSession = Depends(get_session),
) -> User | None:
    if not token:
        return None
    name = read_token(token)
    if not name:
        return None
    row = await db.execute(select(User).where(User.login == name))
    return row.scalar_one_or_none()


async def _must_be_logged_in(user: User | None = Depends(_resolve_user)) -> User:
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Требуется авторизация")
    return user


OptionalUser = Annotated[User | None, Depends(_resolve_user)]
CurrentUser = Annotated[User, Depends(_must_be_logged_in)]

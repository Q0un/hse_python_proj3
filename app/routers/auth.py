from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from ..deps import DB
from ..models import User
from ..schemas import SignupIn, TokenOut, UserOut
from ..security import issue_token, pw_hash, pw_verify

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def signup(body: SignupIn, db: DB):
    exists = await db.execute(select(User).where(User.login == body.login))
    if exists.scalar_one_or_none():
        raise HTTPException(400, "Логин уже занят")

    user = User(login=body.login, pw_hash=pw_hash(body.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenOut)
async def login(body: SignupIn, db: DB):
    row = await db.execute(select(User).where(User.login == body.login))
    user = row.scalar_one_or_none()
    if not user or not pw_verify(body.password, user.pw_hash):
        raise HTTPException(401, "Неправильный логин или пароль")
    return TokenOut(access_token=issue_token(user.login))

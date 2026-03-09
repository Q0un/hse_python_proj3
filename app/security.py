from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from .settings import cfg


def pw_hash(raw: str) -> str:
    return bcrypt.hashpw(raw.encode(), bcrypt.gensalt()).decode()


def pw_verify(raw: str, hashed: str) -> bool:
    return bcrypt.checkpw(raw.encode(), hashed.encode())


def issue_token(login: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=cfg.token_lifetime_min)
    return jwt.encode({"sub": login, "exp": exp}, cfg.jwt_secret, algorithm=cfg.jwt_algo)


def read_token(token: str) -> str | None:
    try:
        data = jwt.decode(token, cfg.jwt_secret, algorithms=[cfg.jwt_algo])
        return data.get("sub")
    except JWTError:
        return None

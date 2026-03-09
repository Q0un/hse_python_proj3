from datetime import datetime

from pydantic import BaseModel, HttpUrl


class SignupIn(BaseModel):
    login: str
    password: str


class UserOut(BaseModel):
    id: int
    login: str
    registered_at: datetime

    model_config = {"from_attributes": True}


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ShortenIn(BaseModel):
    url: HttpUrl
    alias: str | None = None
    expires_at: datetime | None = None


class UpdateTargetIn(BaseModel):
    url: HttpUrl


class ShortLinkOut(BaseModel):
    code: str
    target: str
    created_at: datetime
    expires_at: datetime | None = None

    model_config = {"from_attributes": True}


class StatsOut(BaseModel):
    code: str
    target: str
    created_at: datetime
    visited_at: datetime | None = None
    hits: int
    expires_at: datetime | None = None
    active: bool

    model_config = {"from_attributes": True}


class ExpiredOut(BaseModel):
    code: str
    target: str
    created_at: datetime
    expires_at: datetime | None
    visited_at: datetime | None
    hits: int

    model_config = {"from_attributes": True}


class CleanupIn(BaseModel):
    days: int

import pytest
from httpx import AsyncClient


async def test_signup_ok(client: AsyncClient):
    r = await client.post("/auth/signup", json={"login": "admin", "password": "admin"})
    assert r.status_code == 201
    data = r.json()
    assert data["login"] == "admin"
    assert "id" in data
    assert "registered_at" in data


async def test_signup_duplicate(client: AsyncClient):
    await client.post("/auth/signup", json={"login": "admin", "password": "admin"})
    r = await client.post("/auth/signup", json={"login": "admin", "password": "admin2"})
    assert r.status_code == 400


async def test_signup_missing_fields(client: AsyncClient):
    r = await client.post("/auth/signup", json={"login": "admin"})
    assert r.status_code == 422


async def test_login_ok(client: AsyncClient):
    await client.post("/auth/signup", json={"login": "admin", "password": "admin"})
    r = await client.post("/auth/login", json={"login": "admin", "password": "admin"})
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


async def test_login_wrong_password(client: AsyncClient):
    await client.post("/auth/signup", json={"login": "admin", "password": "admin"})
    r = await client.post("/auth/login", json={"login": "admin", "password": "wrong"})
    assert r.status_code == 401


async def test_login_nonexistent(client: AsyncClient):
    r = await client.post("/auth/login", json={"login": "admon", "password": "admin"})
    assert r.status_code == 401

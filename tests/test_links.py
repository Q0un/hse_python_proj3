from datetime import datetime, timedelta, timezone

from httpx import AsyncClient


async def _auth_header(client: AsyncClient, login="admin", password="admin") -> dict:
    await client.post("/auth/signup", json={"login": login, "password": password})
    r = await client.post("/auth/login", json={"login": login, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# Shorten


async def test_shorten_anonymous(client: AsyncClient):
    r = await client.post("/links/shorten", json={"url": "https://ya.ru/"})
    assert r.status_code == 201
    assert "code" in r.json()
    assert r.json()["target"] == "https://ya.ru/"


async def test_shorten_auth(client: AsyncClient):
    hdr = await _auth_header(client)
    r = await client.post(
        "/links/shorten", json={"url": "https://ya.ru/"}, headers=hdr
    )
    assert r.status_code == 201
    assert "code" in r.json()
    assert r.json()["target"] == "https://ya.ru/"


async def test_shorten_custom_alias(client: AsyncClient):
    r = await client.post(
        "/links/shorten", json={"url": "https://ya.ru/", "alias": "ya"}
    )
    assert r.status_code == 201
    assert r.json()["code"] == "ya"


async def test_shorten_duplicate(client: AsyncClient):
    await client.post(
        "/links/shorten", json={"url": "https://a.ru/", "alias": "dup"}
    )
    r = await client.post(
        "/links/shorten", json={"url": "https://b.ru/", "alias": "dup"}
    )
    assert r.status_code == 409


async def test_shorten_with_expires(client: AsyncClient):
    ts = "2030-01-01T00:00:00Z"
    r = await client.post(
        "/links/shorten", 
        json={"url": "https://ya.ru/", "expires_at": ts}
    )
    assert r.status_code == 201
    assert r.json()["expires_at"] == ts


async def test_shorten_invalid_url(client: AsyncClient):
    r = await client.post("/links/shorten", json={"url": "yayaya"})
    assert r.status_code == 422


async def test_shorten_missing_url(client: AsyncClient):
    r = await client.post("/links/shorten", json={})
    assert r.status_code == 422


# Redirect


async def test_redirect_ok(client: AsyncClient):
    await client.post(
        "/links/shorten", json={"url": "https://ya.ru/", "alias": "ya"}
    )
    r = await client.get("/links/ya", follow_redirects=False)
    assert r.status_code == 307
    assert r.headers["location"] == "https://ya.ru/"


async def test_redirect_not_found(client: AsyncClient):
    r = await client.get("/links/wrong", follow_redirects=False)
    assert r.status_code == 404


async def test_redirect_expired(client: AsyncClient):
    ts = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    await client.post(
        "/links/shorten",
        json={"url": "https://ya.ru/", "alias": "ya", "expires_at": ts},
    )
    r = await client.get("/links/ya", follow_redirects=False)
    assert r.status_code == 410


async def test_redirect_hits(client: AsyncClient):
    await client.post(
        "/links/shorten", json={"url": "https://ya.ru/", "alias": "ya"}
    )
    await client.get("/links/ya", follow_redirects=False)
    await client.get("/links/ya", follow_redirects=False)
    r = await client.get("/links/ya/stats")
    assert r.json()["hits"] == 2


async def test_redirect_cache(client: AsyncClient):
    await client.post(
        "/links/shorten", json={"url": "https://ya.ru/", "alias": "ya"}
    )
    await client.get("/links/ya", follow_redirects=False)
    r = await client.get("/links/ya", follow_redirects=False)
    assert r.status_code == 307


# Stats


async def test_stats_ok(client: AsyncClient):
    await client.post(
        "/links/shorten", json={"url": "https://ya.ru/", "alias": "ya"}
    )
    r = await client.get("/links/ya/stats")
    assert r.status_code == 200
    d = r.json()
    assert d["code"] == "ya"
    assert d["active"] is True
    assert d["hits"] == 0


async def test_stats_not_found(client: AsyncClient):
    r = await client.get("/links/wrong/stats")
    assert r.status_code == 404


async def test_stats_cached(client: AsyncClient):
    await client.post(
        "/links/shorten", json={"url": "https://ya.ru/", "alias": "ya"}
    )
    await client.get("/links/ya/stats")
    r = await client.get("/links/ya/stats")
    assert r.status_code == 200


# Search


async def test_search_found(client: AsyncClient):
    await client.post(
        "/links/shorten", json={"url": "https://ya.ru/", "alias": "ya"}
    )
    r = await client.get(
        "/links/search", params={"original_url": "https://ya.ru/"}
    )
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["code"] == "ya"


async def test_search_not_found(client: AsyncClient):
    r = await client.get(
        "/links/search", params={"original_url": "https://ya.ru/"}
    )
    assert r.status_code == 404


async def test_search_invalid_url(client: AsyncClient):
    r = await client.get("/links/search", params={"original_url": "yayaya"})
    assert r.status_code == 400


async def test_search_cached(client: AsyncClient):
    await client.post(
        "/links/shorten", json={"url": "https://ya.ru/", "alias": "ya"}
    )
    await client.get(
        "/links/search", params={"original_url": "https://ya.ru/"}
    )
    r = await client.get(
        "/links/search", params={"original_url": "https://ya.ru/"}
    )
    assert r.status_code == 200


# ── update ───────────────────────────────────────────────


async def test_update_ok(client: AsyncClient):
    hdr = await _auth_header(client)
    await client.post(
        "/links/shorten",
        json={"url": "https://old.com", "alias": "upd"},
        headers=hdr,
    )
    r = await client.put(
        "/links/upd", json={"url": "https://new.com"}, headers=hdr
    )
    assert r.status_code == 200
    assert "new.com" in r.json()["target"]


async def test_update_unauthorized(client: AsyncClient):
    await client.post(
        "/links/shorten", json={"url": "https://old.com", "alias": "u2"}
    )
    r = await client.put("/links/u2", json={"url": "https://new.com"})
    assert r.status_code == 401


async def test_update_wrong_owner(client: AsyncClient):
    hdr_a = await _auth_header(client, "aaa", "aaa")
    hdr_b = await _auth_header(client, "bbb", "bbb")
    await client.post(
        "/links/shorten",
        json={"url": "https://a.com", "alias": "ow"},
        headers=hdr_a,
    )
    r = await client.put(
        "/links/ow", json={"url": "https://b.com"}, headers=hdr_b
    )
    assert r.status_code == 403


# ── delete ───────────────────────────────────────────────


async def test_delete_ok(client: AsyncClient):
    hdr = await _auth_header(client)
    await client.post(
        "/links/shorten",
        json={"url": "https://del.com", "alias": "rm"},
        headers=hdr,
    )
    r = await client.delete("/links/rm", headers=hdr)
    assert r.status_code == 204
    r2 = await client.get("/links/rm", follow_redirects=False)
    assert r2.status_code == 404


async def test_delete_unauthorized(client: AsyncClient):
    await client.post(
        "/links/shorten", json={"url": "https://del.com", "alias": "d2"}
    )
    r = await client.delete("/links/d2")
    assert r.status_code == 401


async def test_delete_wrong_owner(client: AsyncClient):
    hdr_a = await _auth_header(client, "xx", "xx")
    hdr_b = await _auth_header(client, "yy", "yy")
    await client.post(
        "/links/shorten",
        json={"url": "https://a.com", "alias": "do"},
        headers=hdr_a,
    )
    r = await client.delete("/links/do", headers=hdr_b)
    assert r.status_code == 403


# ── expired history ──────────────────────────────────────


async def test_expired_history(client: AsyncClient):
    exp = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    await client.post(
        "/links/shorten",
        json={"url": "https://exp.com", "alias": "eh", "expires_at": exp},
    )
    await client.get("/links/eh", follow_redirects=False)
    r = await client.get("/links-expired")
    assert r.status_code == 200
    assert any(item["code"] == "eh" for item in r.json())


async def test_expired_history_empty(client: AsyncClient):
    r = await client.get("/links-expired")
    assert r.status_code == 200
    assert r.json() == []


# ── cleanup ──────────────────────────────────────────────


async def test_cleanup_deactivates_stale(client: AsyncClient):
    hdr = await _auth_header(client)
    await client.post(
        "/links/shorten",
        json={"url": "https://stale.com", "alias": "stale"},
        headers=hdr,
    )
    r = await client.post("/links-cleanup", json={"days": 0}, headers=hdr)
    assert r.status_code == 200
    assert r.json()["deactivated"] >= 1


async def test_cleanup_unauthorized(client: AsyncClient):
    r = await client.post("/links-cleanup", json={"days": 0})
    assert r.status_code == 401


async def test_cleanup_default_days(client: AsyncClient):
    hdr = await _auth_header(client)
    r = await client.post("/links-cleanup", headers=hdr)
    assert r.status_code == 200


# ── ping ─────────────────────────────────────────────────


async def test_ping(client: AsyncClient):
    r = await client.get("/ping")
    assert r.status_code == 200

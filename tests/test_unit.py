from app.security import pw_hash, pw_verify, issue_token, read_token
from app.routers.urls import _generate_short_code


def test_pw_hash_returns_string():
    h = pw_hash("secret")
    assert isinstance(h, str)
    assert h != "secret"


def test_pw_verify_correct():
    h = pw_hash("secret")
    assert pw_verify("secret", h) is True


def test_pw_verify_wrong():
    h = pw_hash("secret")
    assert pw_verify("wrong", h) is False


def test_pw_hash_unique_salts():
    h1 = pw_hash("secret")
    h2 = pw_hash("secret")
    assert h1 != h2


def test_issue_and_read_token():
    token = issue_token("secret")
    assert read_token(token) == "secret"


def test_read_token_invalid():
    assert read_token("not-a-token") is None


def test_read_token_empty():
    assert read_token("") is None


def test_read_token_corrupted():
    token = issue_token("secret")
    corrupted = token[:-4] + "XXXX"
    assert read_token(corrupted) is None


def test_generate_short_code():
    code = _generate_short_code("https://ya.ru/")
    assert len(code) == 6
    assert all(c in "0123456789abcdef" for c in code)


def test_generate_short_code_different_each_time():
    codes = {_generate_short_code("https://ya.ru/") for _ in range(30)}
    assert len(codes) == 30

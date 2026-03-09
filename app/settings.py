from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    db_url: str = None
    redis_url: str = None
    jwt_secret: str = None
    jwt_algo: str = "HS256"
    token_lifetime_min: int = 60
    code_length: int = 6
    inactive_days_limit: int = 30
    cache_ttl_sec: int = 600

    model_config = {"env_file": ".env", "extra": "ignore"}


cfg = AppSettings()

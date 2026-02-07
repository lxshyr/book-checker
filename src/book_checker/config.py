from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str
    openai_model: str = "gpt-4o"
    openai_base_url: str | None = None

    model_config = {"env_file": ".env"}


@lru_cache
def get_settings() -> Settings:
    return Settings()

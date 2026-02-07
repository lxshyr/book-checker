from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str
    openai_model: str = "gpt-4o"
    openai_base_url: str | None = None

    vega_api_url: str = (
        "https://na5.iiivega.com/api/search-result/search/format-groups"
    )
    vega_customer_domain: str = "mvpl.na5.iiivega.com"
    vega_host_domain: str = "librarycatalog.mountainview.gov"

    model_config = {"env_file": ".env"}


@lru_cache
def get_settings() -> Settings:
    return Settings()

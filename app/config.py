from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    request_timeout_seconds: int = 12
    max_pages_to_scan: int = 3
    user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    )

    database_url: str | None = None
    persist_enabled: bool = False

    bing_search_api_key: str | None = None
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.0-flash-exp"

    model_config = SettingsConfigDict(env_prefix="", env_file=".env", env_file_encoding="utf-8")


settings = Settings()

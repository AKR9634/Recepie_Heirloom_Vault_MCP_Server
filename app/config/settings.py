from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    database_url: str = "postgresql://postgres:postgres@localhost:5433/recipe_vault"
    mcp_server_name: str = "Recipe Heirloom Vault"
    huggingface_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    huggingfacehub_api_token: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()

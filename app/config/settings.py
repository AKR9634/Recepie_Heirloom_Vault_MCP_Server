from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    database_url: str = "postgresql://postgres:Akhil6july2003%40@db.vdnwpiegigckxvxaukld.supabase.co:5432/postgres"
    mcp_server_name: str = "Recipe Heirloom Vault"
    huggingface_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    huggingfacehub_api_token: str = ""
    openrouter_api_key: str = ""
    food_analysis_model: str = "qwen/qwen2.5-vl-72b-instruct"


@lru_cache
def get_settings() -> Settings:
    return Settings()

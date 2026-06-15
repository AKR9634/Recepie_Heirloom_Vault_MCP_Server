import asyncio
import os
from functools import lru_cache

from langchain_huggingface import HuggingFaceEmbeddings

from app.config.settings import get_settings

EMBEDDING_DIMENSIONS = 384


@lru_cache
def _get_embeddings_model() -> HuggingFaceEmbeddings:
    settings = get_settings()

    if settings.huggingfacehub_api_token:
        os.environ.setdefault("HUGGINGFACEHUB_API_TOKEN", settings.huggingfacehub_api_token)
        os.environ.setdefault("HF_TOKEN", settings.huggingfacehub_api_token)

    return HuggingFaceEmbeddings(
        model_name=settings.huggingface_embedding_model,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def _embed_sync(text: str) -> list[float]:
    model = _get_embeddings_model()
    return model.embed_query(text)


async def warmup_embeddings() -> None:
    """Load the embedding model at startup so tool calls stay fast."""
    await asyncio.to_thread(_get_embeddings_model)


async def generate_embedding(text: str) -> list[float]:
    """Generate an embedding vector for the given text using Hugging Face."""
    try:
        return await asyncio.to_thread(_embed_sync, text)
    except Exception as exc:
        raise RuntimeError(f"Hugging Face embedding failed: {exc}") from exc

import asyncio
import os
from functools import lru_cache

from langchain_core.messages import HumanMessage
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

from app.config.settings import get_settings

STORY_MODEL_REPO = "meta-llama/Llama-3.1-8B-Instruct"

RECIPE_STORY_PROMPT = """You are a culinary historian and cookbook writer.

Write a short narrative about the following recipe.

Recipe Title:
{title}

Region:
{region}

Occasion:
{occasion}

Recipe:
{recipe_text}

Requirements:

* 2 to 3 paragraphs
* Warm and informative tone
* Focus on culinary heritage
* Focus on cultural significance
* Mention traditions when appropriate
* Mention occasions when appropriate
* Feel like an introduction in a family cookbook

Do NOT:

* Invent personal family members
* Fabricate historical facts
* Create fictional events
* Use bullet points
* Use markdown

Keep the response under 250 words."""


def _format_optional(value: str | None) -> str:
    if value and value.strip():
        return value.strip()
    return "Not specified"


def build_recipe_story_prompt(
    title: str,
    recipe_text: str,
    region: str | None = None,
    occasion: str | None = None,
) -> str:
    return RECIPE_STORY_PROMPT.format(
        title=title.strip(),
        region=_format_optional(region),
        occasion=_format_optional(occasion),
        recipe_text=recipe_text.strip(),
    )


@lru_cache
def get_story_model() -> ChatHuggingFace:
    settings = get_settings()

    if settings.huggingfacehub_api_token:
        os.environ.setdefault("HUGGINGFACEHUB_API_TOKEN", settings.huggingfacehub_api_token)
        os.environ.setdefault("HF_TOKEN", settings.huggingfacehub_api_token)

    llm = HuggingFaceEndpoint(
        repo_id=STORY_MODEL_REPO,
        task="text-generation",
    )
    return ChatHuggingFace(llm=llm)


def _generate_story_sync(prompt: str) -> str:
    model = get_story_model()
    response = model.invoke([HumanMessage(content=prompt)])
    content = response.content

    if isinstance(content, str):
        story = content.strip()
    else:
        story = str(content).strip()

    if not story:
        raise ValueError("Model returned an empty story")

    return story


async def generate_recipe_story(
    title: str,
    recipe_text: str,
    region: str | None = None,
    occasion: str | None = None,
) -> str:
    prompt = build_recipe_story_prompt(
        title=title,
        recipe_text=recipe_text,
        region=region,
        occasion=occasion,
    )

    try:
        return await asyncio.to_thread(_generate_story_sync, prompt)
    except ValueError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Hugging Face story generation failed: {exc}") from exc


async def warmup_story_model() -> None:
    """Load the story model at startup so the first tool call stays fast."""
    await asyncio.to_thread(get_story_model)

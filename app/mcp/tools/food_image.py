import asyncio
import base64
import json
import httpx
from pathlib import Path

from fastmcp import FastMCP
from openai import OpenAI

from app.config.settings import get_settings
from app.mcp.tools.recipes import create_recipe_with_embedding

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

FOOD_ANALYSIS_PROMPT = """You are a culinary vision assistant. Analyze the food image and identify the prepared dish.

Your task:
1. Identify the most likely dish name.
2. Provide a confidence score from 0.0 to 1.0.
3. Suggest alternative dish candidates when uncertain (empty list if confident).
4. Separate visible ingredients (clearly seen in the image) from inferred ingredients (typical but not visible).
5. Generate a reasonable estimated recipe for how this dish is commonly made.
6. Provide useful metadata about the dish.

Return ONLY valid JSON with this exact structure (no markdown, no code fences, no explanations):

{
  "dish_name": "",
  "confidence": 0.0,
  "possible_alternatives": [],
  "cuisine": "",
  "visible_ingredients": [],
  "inferred_ingredients": [],
  "estimated_recipe": {
    "ingredients": [],
    "instructions": []
  },
  "metadata": {
    "meal_type": "",
    "difficulty": "",
    "estimated_prep_time": "",
    "estimated_cook_time": ""
  }
}"""

_MIME_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def _guess_mime_type(path: Path) -> str:
    return _MIME_TYPES.get(path.suffix.lower(), "application/octet-stream")


def image_to_data_url(image_path: str) -> str:
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    mime_type = _guess_mime_type(path)
    if mime_type == "application/octet-stream":
        raise ValueError(f"Unsupported image format: {path.suffix}")

    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


async def image_url_to_data_url(image_url: str) -> str:
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(image_url)

    response.raise_for_status()

    content_type = response.headers.get(
        "content-type",
        "image/jpeg",
    )

    encoded = base64.b64encode(response.content).decode("ascii")

    return f"data:{content_type};base64,{encoded}"


def _create_openrouter_client() -> OpenAI:
    settings = get_settings()

    print("API KEY PRESENT:", bool(settings.openrouter_api_key))

    if not settings.openrouter_api_key:
        raise ValueError("OPENROUTER_API_KEY is not configured")

    return OpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=settings.openrouter_api_key,
    )


def _call_food_analysis_model_sync(image_data_url: str) -> str:
    settings = get_settings()
    client = _create_openrouter_client()

    print("MODEL:", settings.food_analysis_model)

    response = client.chat.completions.create(
        model=settings.food_analysis_model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": FOOD_ANALYSIS_PROMPT},
                    {"type": "image_url", "image_url": {"url": image_data_url}},
                ],
            }
        ],
        temperature=0.2,
        max_tokens=1000,
    )

    content = response.choices[0].message.content

    print("CONTENT: ", content)
    
    if not content or not content.strip():
        raise ValueError("Model returned an empty response")

    return content.strip()


async def call_food_analysis_model(image_data_url: str) -> str:
    try:
        return await asyncio.to_thread(
            _call_food_analysis_model_sync,
            image_data_url,
        )
    except ValueError:
        raise
    except Exception as exc:
        raise RuntimeError(f"OpenRouter API error: {exc}") from exc


def _strip_json_wrapper(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()
    if lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _require_str(data: dict, field: str) -> str | None:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        return f"Missing or invalid field: {field}"
    return None


def _require_list(data: dict, field: str) -> str | None:
    value = data.get(field)
    if not isinstance(value, list):
        return f"Missing or invalid field: {field}"
    return None


def _validate_analysis(analysis: dict) -> str | None:
    if not isinstance(analysis, dict):
        return "Model response must be a JSON object"

    if error := _require_str(analysis, "dish_name"):
        return error

    confidence = analysis.get("confidence")
    if not isinstance(confidence, (int, float)):
        return "Missing or invalid field: confidence"
    if not 0.0 <= float(confidence) <= 1.0:
        return "Field confidence must be between 0.0 and 1.0"

    for field in ("possible_alternatives", "visible_ingredients", "inferred_ingredients"):
        if error := _require_list(analysis, field):
            return error

    if not isinstance(analysis.get("cuisine"), str):
        return "Missing or invalid field: cuisine"

    recipe = analysis.get("estimated_recipe")
    if not isinstance(recipe, dict):
        return "Missing or invalid field: estimated_recipe"
    if _require_list(recipe, "ingredients") or _require_list(recipe, "instructions"):
        return "estimated_recipe must include ingredients and instructions lists"

    metadata = analysis.get("metadata")
    if not isinstance(metadata, dict):
        return "Missing or invalid field: metadata"

    for field in ("meal_type", "difficulty", "estimated_prep_time", "estimated_cook_time"):
        if not isinstance(metadata.get(field), str):
            return f"Missing or invalid metadata field: {field}"

    return None


def parse_model_response(response_text: str) -> dict:
    if not response_text or not response_text.strip():
        raise ValueError("Empty model response")

    try:
        parsed = json.loads(_strip_json_wrapper(response_text))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in model response: {exc}") from exc

    validation_error = _validate_analysis(parsed)
    if validation_error:
        raise ValueError(validation_error)

    return parsed


def analysis_to_recipe_text(analysis: dict) -> str:
    recipe = analysis["estimated_recipe"]
    ingredients = recipe["ingredients"]
    instructions = recipe["instructions"]

    lines = ["Ingredients:", ""]
    for item in ingredients:
        lines.append(f"* {item}")

    lines.extend(["", "Instructions:", ""])
    for index, step in enumerate(instructions, start=1):
        step_text = str(step).strip()
        if step_text and step_text[-1] not in ".!?":
            step_text = f"{step_text}."
        lines.append(f"{index}. {step_text}")

    return "\n".join(lines)


async def run_food_image_analysis(image_path: str | None = None, image_url: str | None = None,) -> dict:
    
    if image_url:
        try:
            data_url = await image_url_to_data_url(image_url.strip())
        except Exception as exc:
            return {
                "status": "error",
                "message": f"Unable to download image: {exc}",
            }

    elif image_path:
        try:
            data_url = image_to_data_url(image_path.strip())
        except FileNotFoundError:
            return {
                "status": "error",
                "message": "Unable to analyze image: file not found",
            }
        except (OSError, ValueError) as exc:
            return {
                "status": "error",
                "message": f"Unable to analyze image: {exc}",
            }

    else:
        return {
            "status": "error",
            "message": "Provide image_path or image_url",
        }
    try:
        response_text = await call_food_analysis_model(data_url)
    except ValueError as exc:
        return {"status": "error", "message": str(exc)}
    except RuntimeError as exc:
        print("\nRUNTIME ERROR:")
        print(exc)
        return {"status": "error", "message": str(exc)}

    try:
        analysis = parse_model_response(response_text)
    except ValueError as exc:
        return {"status": "error", "message": str(exc)}

    return {"status": "success", "analysis": analysis}


def register_tools(mcp: FastMCP) -> None:
    @mcp.tool
    async def analyze_food_image(image_path: str | None = None, image_url: str | None = None) -> dict:
        """Identify a prepared dish from a food image and estimate how it is commonly made."""
        return await run_food_image_analysis(image_path=image_path, image_url=image_url)
    
    @mcp.tool
    async def save_analyzed_recipe(image_path: str | None = None, image_url: str | None = None) -> dict:
        """Analyze a food image and save the estimated recipe to the heirloom vault."""
        analysis_result = await run_food_image_analysis(image_path=image_path, image_url=image_url)
        if analysis_result["status"] == "error":
            return analysis_result

        analysis = analysis_result["analysis"]
        title = analysis["dish_name"].strip()
        recipe_text = analysis_to_recipe_text(analysis)
        cuisine = analysis.get("cuisine", "").strip()
        metadata = analysis.get("metadata", {})
        meal_type = metadata.get("meal_type", "").strip()

        create_result = await create_recipe_with_embedding(
            title=title,
            recipe_text=recipe_text,
            region=cuisine or None,
            occasion=meal_type or None,
            fail_on_embedding_error=True,
            success_message="Recipe successfully created from image",
        )

        if create_result["status"] == "error":
            return {"status": "error", "message": "Failed to create recipe from image"}

        return {
            "status": "success",
            "recipe_id": create_result["recipe_id"],
            "title": create_result["title"],
            "message": "Recipe successfully created from image",
        }

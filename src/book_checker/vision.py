import base64
import json
import logging
import re
from pathlib import Path

import openai

from book_checker.config import Settings, get_settings
from book_checker.models import IdentifiedBook

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a book identification assistant. You will be shown an image that \
contains one or more books (e.g. a bookshelf, a stack of books, or books \
spread on a table).

For **every** book you can identify in the image, return a JSON array of \
objects. Each object must have exactly these fields:

- "title"      (string)        – the book title
- "author"     (string | null) – the author, if visible or recognisable
- "series"     (string | null) – the series name, if applicable
- "confidence" (number)        – your confidence from 0.0 to 1.0
- "notes"      (string | null) – anything helpful (e.g. "spine partially \
hidden", "edition uncertain")

Rules:
1. Return ONLY the JSON array – no markdown fences, no commentary.
2. If a book's spine or cover is partially occluded, still include it with \
a lower confidence and a note explaining the uncertainty.
3. Do NOT invent books that are not visible in the image.
4. Order the list roughly by position in the image (left-to-right, \
top-to-bottom).
"""

_FENCE_RE = re.compile(r"```(?:json)?\s*\n?(.*?)\n?\s*```", re.DOTALL)


def parse_vlm_response(text: str) -> list[IdentifiedBook]:
    """Parse a VLM response into a list of IdentifiedBook models.

    Handles responses that may be wrapped in markdown code fences
    (```json ... ```) and strips them before parsing.
    """
    text = text.strip()

    # Strip markdown code fences if present.
    match = _FENCE_RE.search(text)
    if match:
        text = match.group(1).strip()

    raw: list[dict] = json.loads(text)
    return [IdentifiedBook(**item) for item in raw]


_MIME_TYPES: dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}


def _encode_image(path: Path) -> tuple[str, str]:
    """Read an image file and return (base64_data, mime_type)."""
    suffix = path.suffix.lower()
    mime = _MIME_TYPES.get(suffix)
    if mime is None:
        raise ValueError(f"Unsupported image format: {suffix}")
    data = path.read_bytes()
    return base64.b64encode(data).decode(), mime


async def identify_books(
    image_path: str | Path,
    *,
    settings: Settings | None = None,
) -> list[IdentifiedBook]:
    """Send an image to the VLM and return identified books.

    Uses ``openai.AsyncOpenAI`` so it works with both the OpenAI API
    and any OpenAI-compatible backend (e.g. vLLM) by setting
    ``openai_base_url`` in the project settings.
    """
    settings = settings or get_settings()
    image_path = Path(image_path)

    b64_data, mime = _encode_image(image_path)
    image_url = f"data:{mime};base64,{b64_data}"

    client = openai.AsyncOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
    )

    logger.info("Sending %s to VLM model %s", image_path.name, settings.openai_model)

    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": image_url, "detail": "high"},
                    },
                    {
                        "type": "text",
                        "text": "Identify every book visible in this image.",
                    },
                ],
            },
        ],
    )

    text = response.choices[0].message.content or ""
    logger.debug("VLM raw response:\n%s", text)

    return parse_vlm_response(text)

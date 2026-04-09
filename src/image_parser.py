from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

from openai import OpenAI


VISION_PROMPT = """
You are a legal document transcription engine.

Read the contract image carefully and extract the full document text as faithfully as possible.
Requirements:
- Preserve section numbers, headings, clause order, and paragraph boundaries.
- Preserve names, dates, money amounts, percentages, deadlines, and legal qualifiers.
- Do not summarize.
- Do not interpret missing text.
- If a token is unreadable, mark it as [ILLEGIBLE].
- Return plain text only.
""".strip()

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def validate_image_path(image_path: str | Path) -> Path:
    path = Path(image_path).expanduser().resolve()

    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")
    if not path.is_file():
        raise ValueError(f"Expected a file path, got directory: {path}")
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported image extension for {path.name}. Supported: {sorted(SUPPORTED_EXTENSIONS)}"
        )

    return path


def encode_image_to_base64(image_path: str | Path) -> tuple[str, str]:
    path = validate_image_path(image_path)
    mime_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
    return mime_type, encoded


def parse_contract_image(
    image_path: str | Path,
    client: OpenAI,
    model: str,
) -> tuple[str, dict[str, int] | None]:
    path = validate_image_path(image_path)
    mime_type, encoded = encode_image_to_base64(path)

    response = client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": VISION_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{encoded}"},
                    },
                ],
            }
        ],
    )

    content = response.choices[0].message.content or ""
    usage = None
    if response.usage is not None:
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }

    return content.strip(), usage
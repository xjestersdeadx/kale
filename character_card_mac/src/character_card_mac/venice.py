# -*- coding: utf-8 -*-
"""Venice AI OpenAI-compatible client helpers.

Docs: https://docs.venice.ai
Base URL: https://api.venice.ai/api/v1
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from openai import OpenAI

DEFAULT_BASE_URL = "https://api.venice.ai/api/v1"
DEFAULT_MODEL = "zai-org-glm-5-2"


def _load_dotenv(path: Path | None = None) -> None:
    """Load .env into os.environ without overriding existing values."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    candidates: list[Path] = []
    if path is not None:
        candidates.append(path)
    else:
        here = Path(__file__).resolve()
        candidates.extend(
            [
                Path.cwd() / ".env",
                here.parents[3] / ".env",  # repo root when installed from src/
                here.parents[2] / ".env",
            ]
        )
    for candidate in candidates:
        if candidate.is_file():
            load_dotenv(candidate, override=False)
            return


def get_venice_settings() -> dict[str, str]:
    _load_dotenv()
    api_key = os.environ.get("VENICE_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "VENICE_API_KEY is not set. Copy .env.example to .env and add your key."
        )
    base_url = os.environ.get("VENICE_BASE_URL", DEFAULT_BASE_URL).strip() or DEFAULT_BASE_URL
    model = os.environ.get("VENICE_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
    return {"api_key": api_key, "base_url": base_url, "model": model}


def get_venice_client() -> OpenAI:
    settings = get_venice_settings()
    return OpenAI(api_key=settings["api_key"], base_url=settings["base_url"])


def chat_completion(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int | None = 256,
) -> Any:
    """Small OpenAI-compatible /chat/completions call against Venice."""
    settings = get_venice_settings()
    client = get_venice_client()
    kwargs: dict[str, Any] = {
        "model": model or settings["model"],
        "messages": messages,
        "temperature": temperature,
    }
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    return client.chat.completions.create(**kwargs)


def chat_text(prompt: str, *, model: str | None = None) -> str:
    response = chat_completion(
        [{"role": "user", "content": prompt}],
        model=model,
    )
    choice = response.choices[0].message
    return (choice.content or "").strip()

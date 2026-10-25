#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Confirm Venice OpenAI-compatible /chat/completions works."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT / "src"))

# Prefer repo-root .env
from dotenv import load_dotenv

load_dotenv(REPO / ".env", override=False)

from character_card_mac.venice import chat_completion, get_venice_settings


def main() -> int:
    settings = get_venice_settings()
    response = chat_completion(
        [{"role": "user", "content": "Reply with exactly: venice-ok"}],
        max_tokens=32,
        temperature=0,
    )
    text = (response.choices[0].message.content or "").strip()
    print(f"base_url: {settings['base_url']}")
    print(f"model: {settings['model']}")
    print(f"reply: {text}")
    if "venice-ok" not in text.lower() and not text:
        print("unexpected empty reply", file=sys.stderr)
        return 1
    print("venice chat/completions: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

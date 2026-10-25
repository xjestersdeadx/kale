# -*- coding: utf-8 -*-
"""Character-sheet layout templates.

Inspired by ComfyUI-CharacterCardStudio (MIT), simplified for a portable
cell-by-cell pipeline that does not depend on ComfyUI or Qwen-Image.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def _cell(
    cell_id: str,
    label: str,
    role: str,
    prompt: str,
    x: float,
    y: float,
    w: float,
    h: float,
) -> dict[str, Any]:
    return {
        "id": cell_id,
        "label": label,
        "role": role,
        "prompt": prompt,
        "x": x,
        "y": y,
        "w": w,
        "h": h,
    }


TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "turnaround_6",
        "name": "Six-panel turnaround",
        "description": "3 headshots on top, 3 full-body turnaround views below.",
        "width": 1920,
        "height": 1280,
        "defaults": {
            "style": "clean studio character sheet, pure white seamless backdrop, soft key light, consistent identity",
            "background": "#ffffff",
            "accent": "#2f5d50",
        },
        "cells": [
            _cell("head_front", "Front portrait", "portrait", "front head-and-shoulders portrait, facing camera", 0.03, 0.03, 0.303, 0.43),
            _cell("head_side", "Side portrait", "portrait", "strict 90-degree left profile head-and-shoulders", 0.345, 0.03, 0.303, 0.43),
            _cell("head_back", "Back portrait", "portrait", "rear head-and-shoulders, hair/back of head only, no face", 0.66, 0.03, 0.303, 0.43),
            _cell("body_front", "Front body", "turnaround", "front full-body standing pose, head to shoes fully visible", 0.03, 0.52, 0.303, 0.45),
            _cell("body_side", "Side body", "turnaround", "strict 90-degree left profile full-body, head to shoes fully visible", 0.345, 0.52, 0.303, 0.45),
            _cell("body_back", "Back body", "turnaround", "strict 180-degree back full-body, head to shoes fully visible", 0.66, 0.52, 0.303, 0.45),
        ],
    },
    {
        "id": "hero_ref_5",
        "name": "Hero + references",
        "description": "Large hero on the left; two portraits and two bodies on the right.",
        "width": 1920,
        "height": 1200,
        "defaults": {
            "style": "cinematic character key art, clean white studio backdrop, soft rim light",
            "background": "#ffffff",
            "accent": "#8b4513",
        },
        "cells": [
            _cell("hero", "Hero", "hero", "front full-body hero standing pose, head to shoes fully visible, centered", 0.03, 0.06, 0.40, 0.88),
            _cell("head_front", "Front portrait", "portrait", "front head-and-shoulders portrait", 0.47, 0.06, 0.24, 0.40),
            _cell("head_three_quarter", "3/4 portrait", "portrait", "three-quarter head-and-shoulders, face toward camera-right", 0.73, 0.06, 0.24, 0.40),
            _cell("body_side", "Side body", "turnaround", "strict 90-degree left profile full-body", 0.47, 0.52, 0.24, 0.42),
            _cell("body_back", "Back body", "turnaround", "strict 180-degree back full-body", 0.73, 0.52, 0.24, 0.42),
        ],
    },
    {
        "id": "expression_8",
        "name": "Expression spectrum",
        "description": "Four expression portraits on top, four full-body poses below.",
        "width": 1920,
        "height": 1200,
        "defaults": {
            "style": "animation-ready character sheet, white seamless, even lighting",
            "background": "#ffffff",
            "accent": "#355c7d",
        },
        "cells": [
            _cell("ex_neutral", "Neutral", "expression", "neutral calm expression, closed mouth, relaxed brows", 0.03, 0.03, 0.225, 0.43),
            _cell("ex_happy", "Happy", "expression", "open-mouth happy smile, eyes slightly squinted", 0.268, 0.03, 0.225, 0.43),
            _cell("ex_angry", "Angry", "expression", "angry frown, furrowed brows, tense mouth", 0.505, 0.03, 0.225, 0.43),
            _cell("ex_surprised", "Surprised", "expression", "surprised wide eyes, raised brows, open mouth", 0.743, 0.03, 0.225, 0.43),
            _cell("body_front", "Front body", "turnaround", "front full-body standing pose", 0.03, 0.52, 0.225, 0.45),
            _cell("body_side", "Side body", "turnaround", "strict 90-degree left profile full-body", 0.268, 0.52, 0.225, 0.45),
            _cell("body_back", "Back body", "turnaround", "strict 180-degree back full-body", 0.505, 0.52, 0.225, 0.45),
            _cell("body_action", "Action body", "turnaround", "full-body walking or action pose, different from standing", 0.743, 0.52, 0.225, 0.45),
        ],
    },
]

TEMPLATE_BY_ID = {t["id"]: t for t in TEMPLATES}
TEMPLATE_OPTIONS = [f"{t['id']} | {t['name']}" for t in TEMPLATES]
DEFAULT_TEMPLATE_ID = "turnaround_6"

DEFAULT_NEGATIVE = (
    "low quality, blurry, deformed, extra limbs, wrong fingers, identity drift, "
    "face collapse, cropped head, cropped feet, half-body instead of full-body, "
    "collage, multiple panels in one image, text, watermark, logo, border frame"
)


def get_template(template_id: str | None) -> dict[str, Any]:
    return deepcopy(TEMPLATE_BY_ID.get(str(template_id or ""), TEMPLATE_BY_ID[DEFAULT_TEMPLATE_ID]))


def list_templates() -> list[dict[str, str]]:
    return [{"id": t["id"], "name": t["name"], "description": t["description"]} for t in TEMPLATES]

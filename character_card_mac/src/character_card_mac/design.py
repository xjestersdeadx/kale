# -*- coding: utf-8 -*-
"""Build a character-sheet plan JSON that Grok (or any LLM) can fill."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from .templates import DEFAULT_NEGATIVE, DEFAULT_TEMPLATE_ID, get_template


CARD_SCHEMA_VERSION = 1


def build_card_plan(
    *,
    title: str,
    identity: str,
    appearance: str,
    outfit: str = "",
    palette: str = "",
    style: str | None = None,
    template_id: str = DEFAULT_TEMPLATE_ID,
    show_labels: bool = False,
    engine: str = "mflux-flux-schnell-4bit",
    memory_budget_gb: float = 24.0,
    reference_image: str | None = None,
    image_strength: float = 0.45,
) -> dict[str, Any]:
    """Return a portable character-sheet plan.

    This is the artifact Grok Bot should produce. The local Mac runner then
    generates one image per cell and composites them.
    """
    template = get_template(template_id)
    defaults = template.get("defaults", {})
    plan: dict[str, Any] = {
        "version": CARD_SCHEMA_VERSION,
        "title": title.strip() or "Untitled character",
        "templateId": template["id"],
        "identity": identity.strip(),
        "appearance": appearance.strip(),
        "outfit": outfit.strip(),
        "palette": palette.strip(),
        "style": (style or defaults.get("style") or "").strip(),
        "negativePrompt": DEFAULT_NEGATIVE,
        "background": defaults.get("background", "#ffffff"),
        "accent": defaults.get("accent", "#2f5d50"),
        "showLabels": bool(show_labels),
        "width": int(template["width"]),
        "height": int(template["height"]),
        "engine": {
            "name": engine,
            "targetDevice": "apple-silicon",
            "memoryBudgetGB": float(memory_budget_gb),
            "notes": (
                "Prefer FLUX.1-schnell via mflux with --quantize 4 --low-ram. "
                "Generate one cell at a time so peak unified memory stays under ~24GB. "
                "Pass a reference photo for img2img identity lock. "
                "Do not load Qwen-Image 2.1 + Qwen3-VL together on 24GB Apple Silicon."
            ),
        },
        "cells": [],
    }
    if reference_image:
        ref = str(Path(reference_image).expanduser().resolve())
        plan["referenceImage"] = ref
        plan["imageStrength"] = float(image_strength)
        plan["engine"]["referenceImage"] = True
        plan["engine"]["imageStrength"] = float(image_strength)

    for cell in template["cells"]:
        plan["cells"].append(
            {
                "id": cell["id"],
                "label": cell["label"],
                "role": cell["role"],
                "layout": {
                    "x": cell["x"],
                    "y": cell["y"],
                    "w": cell["w"],
                    "h": cell["h"],
                },
                "brief": cell["prompt"],
                "enabled": True,
            }
        )
    return plan


def load_plan(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Card plan must be a JSON object")
    if "templateId" not in data or "cells" not in data:
        raise ValueError("Card plan needs templateId and cells")
    return data


def save_plan(plan: dict[str, Any], path: str | Path) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def merge_grok_overrides(plan: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """Apply optional Grok edits (title/identity/appearance/per-cell briefs)."""
    merged = deepcopy(plan)
    for key in ("title", "identity", "appearance", "outfit", "palette", "style", "negativePrompt"):
        if key in overrides and overrides[key] is not None:
            merged[key] = str(overrides[key]).strip()

    cell_overrides = overrides.get("cells")
    if isinstance(cell_overrides, list):
        by_id = {str(item.get("id")): item for item in cell_overrides if isinstance(item, dict)}
        for cell in merged.get("cells", []):
            extra = by_id.get(str(cell.get("id")))
            if not extra:
                continue
            if "brief" in extra:
                cell["brief"] = str(extra["brief"]).strip()
            if "enabled" in extra:
                cell["enabled"] = bool(extra["enabled"])
            if "label" in extra:
                cell["label"] = str(extra["label"]).strip()
    return merged

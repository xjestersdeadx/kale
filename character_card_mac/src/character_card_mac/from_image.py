# -*- coding: utf-8 -*-
"""One-shot: character photo → sheet plan → generate."""

from __future__ import annotations

import base64
import json
import mimetypes
import re
from pathlib import Path
from typing import Any

from .design import build_card_plan, merge_grok_overrides, save_plan
from .generate import generate_sheet
from .templates import DEFAULT_TEMPLATE_ID


DESCRIBE_PROMPT = """You are designing a visual character reference sheet from one photo.
Return ONLY a JSON object (no markdown) with these keys:
- title: short character name (invent one if unknown)
- identity: 1-2 sentences who they appear to be
- appearance: face, hair, eyes, skin, body — locked visual details from the photo
- outfit: clothing and accessories visible in the photo
- palette: 3-6 color words from the photo
- style: short art direction that matches the photo (e.g. photoreal studio, anime, etc.)
- templateId: one of turnaround_6, hero_ref_5, expression_8

Keep appearance/outfit faithful to the photo so later panels match the same person.
"""


def _data_url(image_path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(image_path))
    if mime not in {"image/png", "image/jpeg", "image/webp", "image/gif"}:
        mime = "image/png"
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return ", ".join(_as_text(item) for item in value if item not in (None, ""))
    if isinstance(value, dict):
        parts = []
        for key, item in value.items():
            text = _as_text(item)
            if text:
                parts.append(f"{key}: {text}")
        return "; ".join(parts)
    return str(value).strip()


def _normalize_character_fields(data: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(data)
    for key in ("title", "identity", "appearance", "outfit", "palette", "style", "templateId"):
        if key in normalized:
            normalized[key] = _as_text(normalized[key])
    return normalized


def _extract_json(text: str) -> dict[str, Any]:
    raw = text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return _normalize_character_fields(data)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", raw)
    if not match:
        raise ValueError("Venice did not return JSON character fields")
    data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ValueError("Venice JSON was not an object")
    return _normalize_character_fields(data)


def describe_character_from_image(
    image_path: str | Path,
    *,
    model: str | None = None,
) -> dict[str, Any]:
    """Ask Venice (vision) to lock identity/appearance from a photo.

    Uses VENICE_VISION_MODEL (default ``qwen3-vl-235b-a22b``). GLM 5.2 is text-only.
    """
    import os

    from .venice import chat_completion

    path = Path(image_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Reference image not found: {path}")

    vision_model = (
        model
        or os.environ.get("VENICE_VISION_MODEL", "").strip()
        or "qwen3-vl-235b-a22b"
    )
    response = chat_completion(
        [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": DESCRIBE_PROMPT},
                    {"type": "image_url", "image_url": {"url": _data_url(path)}},
                ],
            }
        ],
        model=vision_model,
        temperature=0.2,
        max_tokens=900,
    )
    text = (response.choices[0].message.content or "").strip()
    data = _extract_json(text)
    data["_visionModel"] = vision_model
    return data


def attach_reference(
    plan: dict[str, Any],
    image_path: str | Path,
    *,
    image_strength: float = 0.45,
) -> dict[str, Any]:
    path = Path(image_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Reference image not found: {path}")
    plan = dict(plan)
    plan["referenceImage"] = str(path)
    plan["imageStrength"] = float(image_strength)
    engine = dict(plan.get("engine") or {})
    engine["referenceImage"] = True
    engine["imageStrength"] = float(image_strength)
    engine["notes"] = (
        "Reference photo anchors identity via mflux img2img "
        "(--image-path / --image-strength), one cell at a time."
    )
    plan["engine"] = engine
    return plan


def create_sheet_from_image(
    image_path: str | Path,
    output_dir: str | Path,
    *,
    title: str | None = None,
    identity: str | None = None,
    appearance: str | None = None,
    outfit: str | None = None,
    template_id: str = DEFAULT_TEMPLATE_ID,
    backend: str = "mflux",
    describe: bool = True,
    image_strength: float = 0.45,
    seed: int = 42,
    steps: int | None = None,
    quantize: int = 4,
    model: str = "schnell",
    low_ram: bool = True,
    venice_model: str | None = None,
) -> dict[str, Path]:
    """Photo → (optional Venice describe) → plan → generate sheet."""
    path = Path(image_path).expanduser().resolve()
    overrides: dict[str, Any] = {}
    if describe:
        try:
            overrides = describe_character_from_image(path, model=venice_model)
        except Exception as exc:  # noqa: BLE001 - fall back to manual fields
            print(f"[from-image] Venice vision describe failed ({exc}); using text locks / defaults.")
            overrides = {
                "_describeError": str(exc),
                "title": title or path.stem.replace("_", " ").title(),
                "identity": identity or "Original character from reference photo",
                "appearance": appearance
                or "Match the reference photo exactly: same face, hair, skin, and body",
                "outfit": outfit or "Match the clothing and accessories in the reference photo",
                "style": "photoreal character sheet matching the reference photo, clean white studio backdrop",
                "templateId": template_id,
            }

    if title:
        overrides["title"] = title
    if identity:
        overrides["identity"] = identity
    if appearance:
        overrides["appearance"] = appearance
    if outfit:
        overrides["outfit"] = outfit
    if template_id:
        overrides["templateId"] = overrides.get("templateId") or template_id

    plan = build_card_plan(
        title=str(overrides.get("title") or path.stem),
        identity=str(overrides.get("identity") or "Original character from reference photo"),
        appearance=str(
            overrides.get("appearance")
            or "Match the reference photo exactly: same face, hair, skin, and body"
        ),
        outfit=str(overrides.get("outfit") or ""),
        palette=str(overrides.get("palette") or ""),
        style=overrides.get("style"),
        template_id=str(overrides.get("templateId") or template_id),
    )
    plan = merge_grok_overrides(plan, overrides)
    plan = attach_reference(plan, path, image_strength=image_strength)
    if overrides.get("_describeError"):
        plan["describeError"] = overrides["_describeError"]

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    plan_path = save_plan(plan, out / "plan.json")

    gen_steps = steps if steps is not None else (4 if backend == "mflux" else 2)
    paths = generate_sheet(
        plan,
        out,
        backend=backend,
        seed=seed,
        steps=gen_steps,
        quantize=quantize,
        model=model,
        low_ram=low_ram,
        reference_image=path,
        image_strength=image_strength,
    )
    paths["plan"] = plan_path
    return paths

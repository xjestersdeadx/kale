# -*- coding: utf-8 -*-
"""Compile per-cell prompts optimized for FLUX (mflux), not Qwen-Image."""

from __future__ import annotations

from typing import Any


ROLE_FRAMING = {
    "hero": (
        "single character asset photo, one person only, full body from crown to shoes in frame, "
        "subject centered with margin, no collage, no multi-view sheet, no frame borders"
    ),
    "turnaround": (
        "single character asset photo, one person only, full body from crown to shoes in frame, "
        "subject centered with margin, no collage, no multi-view sheet, no frame borders"
    ),
    "portrait": (
        "single head-and-shoulders portrait, one person only, face clearly centered, "
        "no full body, no collage, no frame borders"
    ),
    "expression": (
        "single head-and-shoulders expression study, one person only, face clearly centered, "
        "expression distinct from a neutral face, no full body, no collage, no frame borders"
    ),
    "detail": (
        "single close-up detail crop of clothing, eyes, or accessory only, "
        "no full face portrait, no full body, no collage, no frame borders"
    ),
}


def _clean(text: str) -> str:
    return " ".join(str(text or "").split()).strip(" .;")


def compile_cell_prompt(plan: dict[str, Any], cell: dict[str, Any]) -> str:
    """Build an English FLUX-friendly prompt for one sheet cell."""
    role = str(cell.get("role") or "turnaround")
    framing = ROLE_FRAMING.get(role, ROLE_FRAMING["turnaround"])
    identity = _clean(plan.get("identity") or "")
    appearance = _clean(plan.get("appearance") or "")
    outfit = _clean(plan.get("outfit") or "")
    palette = _clean(plan.get("palette") or "")
    style = _clean(plan.get("style") or "")
    brief = _clean(cell.get("brief") or cell.get("prompt") or "")
    label = _clean(cell.get("label") or cell.get("id") or "asset")

    has_reference = bool(plan.get("referenceImage"))
    parts = [
        f"Same character throughout. Character: {identity}." if identity else "Same original character.",
        (
            "The init/reference photo is the identity anchor: keep the same face, hair, skin tone, "
            "body proportions, clothing, and accessories. Only change camera angle, crop, pose, or expression as requested."
            if has_reference
            else ""
        ),
        f"Appearance lock: {appearance}." if appearance else "",
        f"Outfit lock: {outfit}." if outfit else "",
        f"Color palette: {palette}." if palette else "",
        f"Unified style: {style}." if style else "",
        f"Shot: {label}. {brief}.",
        framing,
        "No text, no numbers, no watermark, no multi-panel character sheet.",
    ]
    return " ".join(part for part in parts if part)


def compile_all_cell_prompts(plan: dict[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for cell in plan.get("cells", []):
        if not cell.get("enabled", True):
            continue
        rows.append(
            {
                "id": str(cell.get("id")),
                "label": str(cell.get("label") or cell.get("id")),
                "role": str(cell.get("role") or ""),
                "prompt": compile_cell_prompt(plan, cell),
                "negative": str(plan.get("negativePrompt") or ""),
            }
        )
    return rows

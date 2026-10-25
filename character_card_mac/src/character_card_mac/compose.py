# -*- coding: utf-8 -*-
"""Compose per-cell images onto a character-sheet canvas."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageColor, ImageDraw, ImageFont, ImageOps


def _rgb(value: str, fallback: tuple[int, int, int]) -> tuple[int, int, int]:
    try:
        return ImageColor.getrgb(value)  # type: ignore[return-value]
    except (ValueError, TypeError):
        return fallback


def _fit(image: Image.Image, size: tuple[int, int], *, contain: bool, background: tuple[int, int, int]) -> Image.Image:
    width, height = max(1, size[0]), max(1, size[1])
    source = image.convert("RGB")
    if contain:
        fitted = ImageOps.contain(source, (width, height), Image.Resampling.LANCZOS)
    else:
        fitted = ImageOps.fit(source, (width, height), Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    canvas = Image.new("RGB", (width, height), background)
    canvas.paste(fitted, ((width - fitted.width) // 2, (height - fitted.height) // 2))
    return canvas


def cell_pixel_box(cell: dict[str, Any], width: int, height: int) -> tuple[int, int, int, int]:
    layout = cell.get("layout") or cell
    x = int(round(float(layout.get("x", 0.0)) * width))
    y = int(round(float(layout.get("y", 0.0)) * height))
    w = max(1, int(round(float(layout.get("w", 1.0)) * width)))
    h = max(1, int(round(float(layout.get("h", 1.0)) * height)))
    return x, y, min(width, x + w), min(height, y + h)


def generation_size(cell: dict[str, Any], card_width: int, card_height: int) -> tuple[int, int]:
    """Return a 16-aligned size matching the cell aspect, capped for 24GB Macs."""
    layout = cell.get("layout") or cell
    target_w = max(1.0, float(layout.get("w", 1.0)) * card_width)
    target_h = max(1.0, float(layout.get("h", 1.0)) * card_height)
    ratio = target_w / target_h
    if ratio >= 1.0:
        width, height = 768.0 * ratio, 768.0
    else:
        width, height = 768.0, 768.0 / max(0.05, ratio)
    scale = min(1.0, 1024.0 / max(width, height))
    width *= scale
    height *= scale

    def aligned(value: float) -> int:
        return max(512, min(1024, int(round(value / 16.0) * 16)))

    return aligned(width), aligned(height)


def compose_card(
    plan: dict[str, Any],
    assets: dict[str, Image.Image],
    *,
    fit_mode: str = "contain",
) -> tuple[Image.Image, dict[str, Any]]:
    width = int(plan.get("width") or 1920)
    height = int(plan.get("height") or 1080)
    background = _rgb(str(plan.get("background") or "#ffffff"), (255, 255, 255))
    accent = _rgb(str(plan.get("accent") or "#2f5d50"), (47, 93, 80))
    canvas = Image.new("RGB", (width, height), background)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, width, max(3, int(height * 0.006))), fill=accent)

    mapping: list[dict[str, Any]] = []
    contain = fit_mode != "cover"
    for index, cell in enumerate(plan.get("cells", [])):
        if not cell.get("enabled", True):
            continue
        cell_id = str(cell.get("id"))
        image = assets.get(cell_id)
        if image is None:
            continue
        x1, y1, x2, y2 = cell_pixel_box(cell, width, height)
        box_w, box_h = max(1, x2 - x1), max(1, y2 - y1)
        role = str(cell.get("role") or "")
        use_contain = contain or role in {"turnaround", "hero", "detail"}
        fitted = _fit(image, (box_w, box_h), contain=use_contain, background=background)
        canvas.paste(fitted, (x1, y1))
        draw.rectangle((x1, y1, x2 - 1, y2 - 1), outline=(210, 214, 219), width=max(1, int(min(width, height) / 1400)))
        if plan.get("showLabels"):
            label = str(cell.get("label") or cell_id)
            draw.rectangle((x1, y2 - 28, x2, y2), fill=(255, 255, 255))
            draw.text((x1 + 8, y2 - 24), label, fill=(40, 40, 40))
        mapping.append({"index": index + 1, "id": cell_id, "label": cell.get("label"), "role": role})

    report = {
        "title": plan.get("title"),
        "templateId": plan.get("templateId"),
        "canvas": [width, height],
        "cells": mapping,
        "engine": plan.get("engine"),
    }
    return canvas, report


def save_report(report: dict[str, Any], path: str | Path) -> Path:
    out = Path(path)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def make_placeholder(size: tuple[int, int], label: str, role: str) -> Image.Image:
    """Deterministic placeholder so the pipeline works without a Mac GPU."""
    palette = {
        "hero": (47, 93, 80),
        "turnaround": (53, 92, 125),
        "portrait": (139, 69, 19),
        "expression": (120, 80, 100),
        "detail": (90, 90, 90),
    }
    color = palette.get(role, (70, 70, 70))
    image = Image.new("RGB", size, color)
    draw = ImageDraw.Draw(image)
    margin = max(8, min(size) // 20)
    draw.rectangle((margin, margin, size[0] - margin, size[1] - margin), outline=(245, 245, 245), width=3)
    try:
        font = ImageFont.load_default()
    except OSError:
        font = None
    text = f"{label}\n({role})"
    draw.multiline_text((margin + 8, margin + 8), text, fill=(245, 245, 245), font=font, spacing=4)
    return image

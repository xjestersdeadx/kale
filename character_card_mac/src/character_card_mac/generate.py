# -*- coding: utf-8 -*-
"""Generate one sheet cell at a time via mflux (Apple Silicon) or placeholders."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageOps

from .compose import compose_card, generation_size, make_placeholder, save_report
from .prompts import compile_all_cell_prompts


def _resolve_reference(
    plan: dict[str, Any],
    reference_image: str | Path | None,
) -> Path | None:
    raw = reference_image or plan.get("referenceImage")
    if not raw:
        return None
    path = Path(str(raw)).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Reference image not found: {path}")
    return path


def _strength_for_role(role: str, default: float) -> float:
    # Keep face closer to the photo; let body/turnaround change pose more freely.
    by_role = {
        "portrait": max(default, 0.5),
        "expression": max(default, 0.48),
        "hero": default,
        "turnaround": min(default, 0.42),
        "detail": min(default, 0.35),
    }
    return float(by_role.get(role, default))


def _run_mflux(
    *,
    prompt: str,
    out_path: Path,
    width: int,
    height: int,
    seed: int,
    steps: int,
    quantize: int,
    model: str,
    low_ram: bool,
    reference_image: Path | None = None,
    image_strength: float = 0.45,
) -> None:
    binary = shutil.which("mflux-generate")
    if binary is None:
        raise RuntimeError(
            "mflux-generate not found. On your M4 Pro Mac Mini install with: "
            "pip install 'mflux>=0.13.0'  (Apple Silicon only)"
        )
    cmd = [
        binary,
        "--prompt",
        prompt,
        "--model",
        model,
        "--steps",
        str(steps),
        "--seed",
        str(seed),
        "--height",
        str(height),
        "--width",
        str(width),
        "--quantize",
        str(quantize),
        "--output",
        str(out_path),
    ]
    if low_ram:
        cmd.append("--low-ram")
    if reference_image is not None:
        # Prefer legacy pair for wider mflux version compatibility.
        cmd.extend(
            [
                "--image-path",
                str(reference_image),
                "--image-strength",
                f"{image_strength:.3f}",
            ]
        )
    subprocess.run(cmd, check=True)


def _placeholder_from_reference(
    reference: Image.Image,
    size: tuple[int, int],
    label: str,
    role: str,
) -> Image.Image:
    fitted = ImageOps.fit(reference.convert("RGB"), size, Image.Resampling.LANCZOS, centering=(0.5, 0.35))
    draw = ImageDraw.Draw(fitted)
    bar_h = max(24, size[1] // 14)
    draw.rectangle((0, 0, size[0], bar_h), fill=(20, 20, 20))
    try:
        font = ImageFont.load_default()
    except OSError:
        font = None
    draw.text((8, 6), f"{label} · {role}", fill=(245, 245, 245), font=font)
    return fitted


def generate_sheet(
    plan: dict[str, Any],
    output_dir: str | Path,
    *,
    backend: str = "placeholder",
    seed: int = 42,
    steps: int = 2,
    quantize: int = 4,
    model: str = "schnell",
    low_ram: bool = True,
    fit_mode: str = "contain",
    reference_image: str | Path | None = None,
    image_strength: float | None = None,
) -> dict[str, Path]:
    """Generate every enabled cell, then compose the final character sheet."""
    out = Path(output_dir)
    cells_dir = out / "cells"
    cells_dir.mkdir(parents=True, exist_ok=True)

    ref_path = _resolve_reference(plan, reference_image)
    strength_default = float(
        image_strength
        if image_strength is not None
        else plan.get("imageStrength") or 0.45
    )
    if ref_path is not None:
        plan = dict(plan)
        plan["referenceImage"] = str(ref_path)
        plan["imageStrength"] = strength_default
        shutil.copy2(ref_path, out / f"reference{ref_path.suffix.lower() or '.png'}")

    prompt_rows = compile_all_cell_prompts(plan)
    (out / "prompts.json").write_text(
        json.dumps(prompt_rows, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    assets: dict[str, Image.Image] = {}
    width = int(plan.get("width") or 1920)
    height = int(plan.get("height") or 1280)
    cell_by_id = {str(cell.get("id")): cell for cell in plan.get("cells", [])}
    ref_pil = Image.open(ref_path).convert("RGB") if ref_path else None

    for index, row in enumerate(prompt_rows):
        cell_id = row["id"]
        cell = cell_by_id[cell_id]
        gen_w, gen_h = generation_size(cell, width, height)
        cell_path = cells_dir / f"{index:02d}_{cell_id}.png"
        cell_seed = (int(seed) + index * 0x9E3779B1) & 0xFFFFFFFF
        role = str(row.get("role") or cell.get("role") or "")
        cell_strength = _strength_for_role(role, strength_default)

        if backend == "mflux":
            _run_mflux(
                prompt=row["prompt"],
                out_path=cell_path,
                width=gen_w,
                height=gen_h,
                seed=cell_seed,
                steps=steps,
                quantize=quantize,
                model=model,
                low_ram=low_ram,
                reference_image=ref_path,
                image_strength=cell_strength,
            )
            assets[cell_id] = Image.open(cell_path).convert("RGB")
        elif backend == "placeholder":
            if ref_pil is not None:
                image = _placeholder_from_reference(ref_pil, (gen_w, gen_h), row["label"], role)
            else:
                image = make_placeholder((gen_w, gen_h), row["label"], role)
            image.save(cell_path)
            assets[cell_id] = image
        else:
            raise ValueError(f"Unknown backend: {backend}")

    card, report = compose_card(plan, assets, fit_mode=fit_mode)
    report["referenceImage"] = str(ref_path) if ref_path else ""
    report["imageStrength"] = strength_default
    card_path = out / "character_sheet.png"
    report_path = out / "report.json"
    card.save(card_path)
    save_report(report, report_path)
    return {"sheet": card_path, "report": report_path, "prompts": out / "prompts.json", "cells": cells_dir}

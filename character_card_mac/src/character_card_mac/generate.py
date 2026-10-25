# -*- coding: utf-8 -*-
"""Generate one sheet cell at a time via mflux (Apple Silicon) or placeholders."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image

from .compose import compose_card, generation_size, make_placeholder, save_report
from .prompts import compile_all_cell_prompts


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
    subprocess.run(cmd, check=True)


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
) -> dict[str, Path]:
    """Generate every enabled cell, then compose the final character sheet."""
    out = Path(output_dir)
    cells_dir = out / "cells"
    cells_dir.mkdir(parents=True, exist_ok=True)

    prompt_rows = compile_all_cell_prompts(plan)
    (out / "prompts.json").write_text(json.dumps(prompt_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    assets: dict[str, Image.Image] = {}
    width = int(plan.get("width") or 1920)
    height = int(plan.get("height") or 1280)
    cell_by_id = {str(cell.get("id")): cell for cell in plan.get("cells", [])}

    for index, row in enumerate(prompt_rows):
        cell_id = row["id"]
        cell = cell_by_id[cell_id]
        gen_w, gen_h = generation_size(cell, width, height)
        cell_path = cells_dir / f"{index:02d}_{cell_id}.png"
        cell_seed = (int(seed) + index * 0x9E3779B1) & 0xFFFFFFFF

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
            )
            assets[cell_id] = Image.open(cell_path).convert("RGB")
        elif backend == "placeholder":
            image = make_placeholder((gen_w, gen_h), row["label"], row["role"])
            image.save(cell_path)
            assets[cell_id] = image
        else:
            raise ValueError(f"Unknown backend: {backend}")

    card, report = compose_card(plan, assets, fit_mode=fit_mode)
    card_path = out / "character_sheet.png"
    report_path = out / "report.json"
    card.save(card_path)
    save_report(report, report_path)
    return {"sheet": card_path, "report": report_path, "prompts": out / "prompts.json", "cells": cells_dir}
